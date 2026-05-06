"""
nlp_embeddings.py

Detección de equivalencias semánticas entre productos de marca propia
y productos comerciales mediante embeddings de sentence-transformers.

Modelo: paraphrase-multilingual-MiniLM-L12-v2
  - Multilingüe (soporta español nativamente)
  - 117MB — ejecutable en CPU sin GPU
  - Genera vectores de 384 dimensiones por título

Metodología:
  1. Generar embedding de cada título de producto
  2. Para cada producto de marca propia, calcular similitud coseno
     con todos los productos comerciales de la misma subcategoría
  3. El producto comercial con mayor similitud es el equivalente

Por qué similitud coseno y no distancia euclidiana:
  Los embeddings de sentence-transformers están optimizados para
  similitud coseno. La distancia euclidiana mezcla dirección y magnitud,
  lo que penaliza títulos de longitud diferente aunque sean semánticamente
  idénticos. El coseno solo mide el ángulo entre vectores.
"""

import pandas as pd
import numpy as np
import logging
import matplotlib.pyplot as plt
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.manifold import TSNE

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────
PARTITIONED_DIR = Path("data/processed")
OUTPUT_EQUIV = Path("data/nlp/equivalencias.parquet")
OUTPUT_EMBEDDINGS = Path("data/nlp/embeddings.parquet")
IMG_DIR = Path("docs/img/nlp")

IMG_DIR.mkdir(parents=True, exist_ok=True)
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = 3  # top-3 equivalentes por producto de marca propia
UMBRAL_SIMILITUD = 0.75  # similitud mínima para considerar equivalencia válida
MIN_COMERCIALES = 3  # mínimo de productos comerciales por subcategoría

MARCAS_PROPIAS = ["hacendado", "bosque verde", "deliplus", "compy"]


# ── Carga del catálogo actual ─────────────────────────────────────────────────
def cargar_catalogo() -> pd.DataFrame:
    """
    Carga solo la última fecha disponible — el catálogo de hoy.
    No necesitamos el histórico completo: los embeddings se calculan
    sobre los títulos actuales, no sobre series temporales.
    """
    df = pd.read_parquet(
        PARTITIONED_DIR,
        columns=[
            "referencia",
            "fecha",
            "titulo",
            "subcategoria",
            "marca_propia",
            "es_marca_propia",
            "precio_actual",
            "precio_por_medida",
            "unidad_medida",
        ],
    )
    df["fecha"] = pd.to_datetime(df["fecha"].astype(str), errors="coerce")

    # Solo la última fecha — catálogo más reciente
    ultima_fecha = df["fecha"].max()
    df = df[df["fecha"] == ultima_fecha].copy()

    log.info(f"Catálogo cargado: {ultima_fecha.date()} | {len(df):,} productos")
    log.info(f"  Marca propia : {df['es_marca_propia'].sum():,}")
    log.info(f"  Comercial    : {(~df['es_marca_propia']).sum():,}")
    return df


# ── Generación de embeddings ──────────────────────────────────────────────────
def generar_embeddings(df: pd.DataFrame) -> tuple:
    """
    Genera un embedding de 384 dimensiones por título de producto.
    El modelo se descarga automáticamente la primera vez (~117MB).

    Preprocesamiento del título antes de embeder:
      - Ya está en minúsculas (ETL)
      - Eliminamos la marca del título para que el embedding capture
        el PRODUCTO, no la marca. Así "leche entera hacendado" y
        "leche entera ram" tienen embeddings más cercanos.
    """
    log.info(f"Cargando modelo: {MODEL_NAME}")
    modelo = SentenceTransformer(MODEL_NAME)

    # Limpiar marca del título para mejorar comparabilidad semántica
    def limpiar_titulo(titulo: str, marca: str) -> str:
        if marca != "comercial":
            titulo = titulo.replace(marca, "").strip()
        return titulo

    df["titulo_limpio"] = df.apply(
        lambda r: limpiar_titulo(r["titulo"], r["marca_propia"]), axis=1
    )

    titulos = df["titulo_limpio"].tolist()
    log.info(f"Generando embeddings para {len(titulos):,} productos...")

    # batch_size=64 equilibra velocidad y uso de RAM en CPU
    embeddings = modelo.encode(
        titulos,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,  # normalizar → coseno = producto escalar
    )

    log.info(f"Embeddings generados: shape {embeddings.shape}")
    return embeddings, modelo


# ── Búsqueda de equivalencias ─────────────────────────────────────────────────
def encontrar_equivalencias(df: pd.DataFrame, embeddings: np.ndarray) -> pd.DataFrame:
    """
    Para cada producto de marca propia, busca los TOP_K productos comerciales
    más similares DENTRO DE LA MISMA SUBCATEGORÍA.

    Por qué dentro de la misma subcategoría:
      Sin este filtro, "leche hacendado" podría emparejarse con "yogur danone"
      porque ambos son lácteos y comparten vocabulario semántico.
      La subcategoría actúa como restricción de dominio.
    """
    df = df.reset_index(drop=True)
    resultados = []

    # Obtenemos las subcategorías donde hay presencia de marca propia
    subcategorias = df[df["es_marca_propia"]]["subcategoria"].unique()
    log.info(f"Buscando equivalencias en {len(subcategorias)} subcategorías...")

    for subcat in subcategorias:
        # Productos de marca propia en esta subcategoría
        mask_mp = (df["subcategoria"] == subcat) & df["es_marca_propia"]
        mask_com = (df["subcategoria"] == subcat) & (~df["es_marca_propia"])

        idx_mp = df[mask_mp].index.tolist()
        idx_com = df[mask_com].index.tolist()

        # Necesitamos suficientes productos comerciales para comparar.
        # Con < 3 comerciales, todos los MP se emparejan con el mismo
        # producto (ej: todos los helados → "cucurucho fresa nata"),
        # generando equivalencias no funcionales.
        if not idx_mp or len(idx_com) < MIN_COMERCIALES:
            continue

        emb_mp = embeddings[idx_mp]  # (n_mp, 384)
        emb_com = embeddings[idx_com]  # (n_com, 384)

        # Matriz de similitud coseno (n_mp × n_com)
        # Como los embeddings están normalizados, coseno = producto escalar
        sim_matrix = cosine_similarity(emb_mp, emb_com)

        for i, idx_p in enumerate(idx_mp):
            producto_mp = df.loc[idx_p]
            sims = sim_matrix[i]  # similitudes con todos los comerciales

            # Top-K índices por similitud descendente
            top_k_local = np.argsort(sims)[::-1][:TOP_K]

            for rank, j in enumerate(top_k_local):
                sim = sims[j]
                if sim < UMBRAL_SIMILITUD:
                    continue  # descartar equivalencias débiles

                idx_c = idx_com[j]
                producto_com = df.loc[idx_c]

                # Precios por unidad de medida (€/kg, €/L)
                pm_mp = producto_mp["precio_por_medida"]
                pm_com = producto_com["precio_por_medida"]
                um_mp = producto_mp["unidad_medida"]
                um_com = producto_com["unidad_medida"]
                tiene_medida = pd.notna(pm_mp) and pd.notna(pm_com)
                misma_unidad = tiene_medida and (um_mp == um_com)

                resultados.append(
                    {
                        # Producto marca propia
                        "ref_mp": producto_mp["referencia"],
                        "titulo_mp": producto_mp["titulo"],
                        "marca_mp": producto_mp["marca_propia"],
                        "precio_mp": producto_mp["precio_actual"],
                        "precio_medida_mp": pm_mp,
                        "unidad_medida_mp": um_mp,
                        # Producto comercial equivalente
                        "ref_com": producto_com["referencia"],
                        "titulo_com": producto_com["titulo"],
                        "precio_com": producto_com["precio_actual"],
                        "precio_medida_com": pm_com,
                        "unidad_medida_com": um_com,
                        # Métricas de comparación
                        "subcategoria": subcat,
                        "similitud": round(float(sim), 4),
                        "rank": rank + 1,
                        "misma_unidad": misma_unidad,
                        # Diferencia de precio absoluto (secundaria)
                        "diferencia_precio": round(
                            producto_com["precio_actual"]
                            - producto_mp["precio_actual"],
                            4,
                        ),
                        "diferencia_precio_pct": round(
                            (
                                producto_com["precio_actual"]
                                - producto_mp["precio_actual"]
                            )
                            / producto_mp["precio_actual"]
                            * 100,
                            2,
                        ),
                        # Diferencia por unidad de medida (métrica principal)
                        # Solo comparable cuando ambos usan la misma unidad
                        "diferencia_por_medida": round(pm_com - pm_mp, 4)
                        if misma_unidad
                        else None,
                        "diferencia_por_medida_pct": round(
                            (pm_com - pm_mp) / pm_mp * 100, 2
                        )
                        if misma_unidad and pm_mp > 0
                        else None,
                    }
                )

    equivalencias = pd.DataFrame(resultados)
    log.info(f"Equivalencias encontradas: {len(equivalencias):,}")
    log.info(f"Pares únicos (rank=1)    : {(equivalencias['rank'] == 1).sum():,}")
    return equivalencias


# ── Resumen de hallazgos ──────────────────────────────────────────────────────
def resumir(equiv: pd.DataFrame) -> None:
    top1 = equiv[equiv["rank"] == 1].copy()

    log.info("─" * 60)
    log.info("RESUMEN NLP — EQUIVALENCIAS MARCA PROPIA ↔ COMERCIAL")
    log.info(f"  Pares encontrados (similitud ≥ {UMBRAL_SIMILITUD}): {len(top1):,}")
    log.info(f"  Similitud media   : {top1['similitud'].mean():.3f}")
    log.info(f"  Similitud mínima  : {top1['similitud'].min():.3f}")
    log.info("")

    # ── Métrica principal: precio por unidad de medida (€/kg, €/L) ──
    # Solo pares con la MISMA unidad de medida — evita comparar
    # €/ud con €/L (ej: toallitas vs líquido → +23100% absurdo)
    top1_medida = top1[
        top1["misma_unidad"] & top1["diferencia_por_medida_pct"].notna()
    ].copy()
    n_comparables = len(top1_medida)
    n_excluidos = len(top1) - n_comparables

    log.info(
        f"  Pares comparables (misma unidad): {n_comparables:,} "
        f"({n_excluidos:,} excluidos por unidad distinta)"
    )
    log.info(
        f"  Precio/medida medio MP     : {top1_medida['precio_medida_mp'].mean():.2f}€"
    )
    log.info(
        f"  Precio/medida medio COM    : {top1_medida['precio_medida_com'].mean():.2f}€"
    )
    # Mediana como métrica principal — robusta frente a outliers
    mediana_pct = top1_medida["diferencia_por_medida_pct"].median()
    media_pct = top1_medida["diferencia_por_medida_pct"].mean()
    log.info(
        f"  Diferencia mediana (medida): {mediana_pct:+.1f}%"
    )
    log.info(
        f"  Diferencia media (medida)  : {media_pct:+.1f}%"
    )
    log.info("")

    # ── Métrica secundaria: precio absoluto (referencia) ──
    top1_precio = top1.dropna(subset=["diferencia_precio"])
    log.info(f"  Precio absoluto medio MP   : {top1_precio['precio_mp'].mean():.2f}€")
    log.info(f"  Precio absoluto medio COM  : {top1_precio['precio_com'].mean():.2f}€")
    log.info(
        f"  Diferencia media (abs.)    : {top1_precio['diferencia_precio'].mean():+.2f}€"
    )
    log.info(
        f"  Diferencia media (abs. %)  : {top1_precio['diferencia_precio_pct'].mean():+.1f}%"
    )
    log.info("")

    # Top subcategorías con mayor brecha — por medida (mediana)
    log.info("  Top 5 subcategorías con mayor brecha (mediana por medida):")
    top_brecha = (
        top1_medida.groupby("subcategoria")["diferencia_por_medida_pct"]
        .median()
        .sort_values(ascending=False)
        .head(5)
    )
    for subcat, pct in top_brecha.items():
        log.info(f"    {subcat:<35} {pct:+.1f}%")

    # Ejemplos concretos — van en la presentación
    log.info("")
    log.info("  Ejemplos de equivalencias (similitud más alta):")
    muestra = top1.nlargest(5, "similitud")[
        ["titulo_mp", "titulo_com", "similitud", "diferencia_por_medida_pct"]
    ]
    for _, row in muestra.iterrows():
        pct_str = (
            f"{row['diferencia_por_medida_pct']:+.1f}%"
            if pd.notna(row["diferencia_por_medida_pct"])
            else "s/d"
        )
        log.info(
            f"    [{row['similitud']:.3f}] {row['titulo_mp'][:35]:<35} ↔ "
            f"{row['titulo_com'][:35]:<35} ({pct_str})"
        )
    log.info("─" * 60)


def generar_visualizaciones(
    equiv: pd.DataFrame, embeddings: np.ndarray, df: pd.DataFrame
) -> None:
    """Genera gráficas diagnósticas de NLP y equivalencias."""
    # 1. Distribución de Similitud Coseno
    plt.figure(figsize=(10, 5))
    plt.hist(equiv["similitud"], bins=50, color="teal", alpha=0.7, edgecolor="white")
    plt.axvline(
        UMBRAL_SIMILITUD,
        color="red",
        linestyle="--",
        label=f"Umbral ({UMBRAL_SIMILITUD})",
    )
    plt.title("Distribución de Similitud Coseno entre Productos")
    plt.xlabel("Similitud")
    plt.ylabel("Frecuencia")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(IMG_DIR / "similitud_distribucion.png", dpi=150)
    plt.close()

    # 2. Brecha de precios por subcategoría — solo pares con misma unidad
    top1 = equiv[equiv["rank"] == 1].copy()
    top1_medida = top1[
        top1["misma_unidad"] & top1["diferencia_por_medida_pct"].notna()
    ]
    counts = top1_medida["subcategoria"].value_counts()
    top_subcats = counts.head(10).index

    brecha = (
        top1_medida[top1_medida["subcategoria"].isin(top_subcats)]
        .groupby("subcategoria")["diferencia_por_medida_pct"]
        .median()
        .sort_values()
    )

    plt.figure(figsize=(12, 6))
    colors = ["crimson" if x > 0 else "forestgreen" for x in brecha.values]
    brecha.plot(kind="barh", color=colors, alpha=0.8)
    plt.title("Brecha de Precio por Medida: Marca Comercial vs Marca Propia")
    plt.xlabel("Diferencia de Precio por Medida (%)")
    plt.ylabel("Subcategoría")
    plt.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(IMG_DIR / "brecha_precios.png", dpi=150)
    plt.close()

    # 3. Proyección de Embeddings (t-SNE) - Muestra de 1000 productos
    log.info("Generando proyección t-SNE de embeddings (esto puede tardar un poco)...")
    n_sample = min(1000, len(embeddings))
    rng = np.random.RandomState(42)
    indices = rng.choice(len(embeddings), n_sample, replace=False)
    emb_sample = embeddings[indices]
    subcats_sample = df.iloc[indices]["subcategoria"].values

    tsne = TSNE(n_components=2, random_state=42, perplexity=30)
    vis_dims = tsne.fit_transform(emb_sample)

    plt.figure(figsize=(12, 10))
    # Colorear por top 10 subcategorías, el resto en gris
    top_10_global = df["subcategoria"].value_counts().head(10).index
    for cat in top_10_global:
        mask = subcats_sample == cat
        plt.scatter(vis_dims[mask, 0], vis_dims[mask, 1], label=cat, alpha=0.6, s=50)

    plt.scatter(
        vis_dims[~np.isin(subcats_sample, top_10_global), 0],
        vis_dims[~np.isin(subcats_sample, top_10_global), 1],
        color="lightgrey",
        alpha=0.2,
        s=20,
        label="Otras",
    )

    plt.title(f"Proyección Semántica de Productos (t-SNE sobre {n_sample} items)")
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", title="Subcategorías")
    plt.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(IMG_DIR / "nlp_proyeccion_embeddings.png", dpi=150)
    plt.close()

    log.info(f"Gráficas guardadas en {IMG_DIR}")


# ── Guardar resultados ────────────────────────────────────────────────────────
def guardar(df: pd.DataFrame, embeddings: np.ndarray, equiv: pd.DataFrame) -> None:
    OUTPUT_EQUIV.parent.mkdir(parents=True, exist_ok=True)

    # Tabla de equivalencias — para Kibana y Flask
    equiv.to_parquet(OUTPUT_EQUIV, index=False)
    log.info(f"Equivalencias guardadas: {OUTPUT_EQUIV}")

    # Embeddings con referencia — para clustering posterior (Sprint 4)
    emb_df = pd.DataFrame(
        embeddings, columns=[f"emb_{i}" for i in range(embeddings.shape[1])]
    )
    emb_df.insert(0, "referencia", df["referencia"].values)
    emb_df.insert(1, "titulo", df["titulo"].values)
    emb_df.insert(2, "marca_propia", df["marca_propia"].values)
    emb_df.insert(3, "subcategoria", df["subcategoria"].values)
    emb_df.to_parquet(OUTPUT_EMBEDDINGS, index=False)
    log.info(f"Embeddings guardados   : {OUTPUT_EMBEDDINGS}")


# ── Entrypoint ────────────────────────────────────────────────────────────────
def ejecutar():
    df = cargar_catalogo()
    embeddings, _ = generar_embeddings(df)
    equiv = encontrar_equivalencias(df, embeddings)
    resumir(equiv)
    generar_visualizaciones(equiv, embeddings, df)
    guardar(df, embeddings, equiv)
    return df, embeddings, equiv


if __name__ == "__main__":
    df, embeddings, equiv = ejecutar()
