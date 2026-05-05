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
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────
PARTITIONED_DIR = Path("data/processed")
OUTPUT_EQUIV = Path("data/nlp/equivalencias.parquet")
OUTPUT_EMBEDDINGS = Path("data/nlp/embeddings.parquet")
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = 3  # top-3 equivalentes por producto de marca propia
UMBRAL_SIMILITUD = 0.75  # similitud mínima para considerar equivalencia válida

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
    df["fecha"] = pd.to_datetime(df["fecha"])

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

    marcas_propias_df = df[df["es_marca_propia"]].copy()
    comerciales_df = df[~df["es_marca_propia"]].copy()

    subcategorias = marcas_propias_df["subcategoria"].unique()
    log.info(f"Buscando equivalencias en {len(subcategorias)} subcategorías...")

    for subcat in subcategorias:
        # Productos de marca propia en esta subcategoría
        mask_mp = (df["subcategoria"] == subcat) & df["es_marca_propia"]
        mask_com = (df["subcategoria"] == subcat) & (~df["es_marca_propia"])

        idx_mp = df[mask_mp].index.tolist()
        idx_com = df[mask_com].index.tolist()

        # Necesitamos al menos 1 de cada tipo para comparar
        if not idx_mp or not idx_com:
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

                resultados.append(
                    {
                        # Producto marca propia
                        "ref_mp": producto_mp["referencia"],
                        "titulo_mp": producto_mp["titulo"],
                        "marca_mp": producto_mp["marca_propia"],
                        "precio_mp": producto_mp["precio_actual"],
                        "precio_medida_mp": producto_mp["precio_por_medida"],
                        # Producto comercial equivalente
                        "ref_com": producto_com["referencia"],
                        "titulo_com": producto_com["titulo"],
                        "precio_com": producto_com["precio_actual"],
                        "precio_medida_com": producto_com["precio_por_medida"],
                        # Métricas de comparación
                        "subcategoria": subcat,
                        "similitud": round(float(sim), 4),
                        "rank": rank + 1,
                        # Diferencia de precio — el insight económico
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
                        "diferencia_por_medida": round(
                            (
                                producto_com["precio_por_medida"]
                                - producto_mp["precio_por_medida"]
                            ),
                            4,
                        )
                        if pd.notna(producto_mp["precio_por_medida"])
                        and pd.notna(producto_com["precio_por_medida"])
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

    # Diferencia de precio — el hallazgo económico principal
    top1_precio = top1.dropna(subset=["diferencia_precio"])
    log.info(f"  Precio medio marca propia  : {top1_precio['precio_mp'].mean():.2f}€")
    log.info(f"  Precio medio comercial     : {top1_precio['precio_com'].mean():.2f}€")
    log.info(
        f"  Diferencia media           : {top1_precio['diferencia_precio'].mean():+.2f}€"
    )
    log.info(
        f"  Diferencia media (%)       : {top1_precio['diferencia_precio_pct'].mean():+.1f}%"
    )
    log.info("")

    # Top subcategorías con mayor brecha
    log.info("  Top 5 subcategorías con mayor brecha de precio:")
    top_brecha = (
        top1_precio.groupby("subcategoria")["diferencia_precio_pct"]
        .mean()
        .sort_values(ascending=False)
        .head(5)
    )
    for subcat, pct in top_brecha.items():
        log.info(f"    {subcat:<35} {pct:+.1f}%")

    # Ejemplos concretos — van en la presentación
    log.info("")
    log.info("  Ejemplos de equivalencias (similitud más alta):")
    muestra = top1.nlargest(5, "similitud")[
        ["titulo_mp", "titulo_com", "similitud", "diferencia_precio_pct"]
    ]
    for _, row in muestra.iterrows():
        log.info(
            f"    [{row['similitud']:.3f}] {row['titulo_mp'][:35]:<35} ↔ "
            f"{row['titulo_com'][:35]:<35} ({row['diferencia_precio_pct']:+.1f}%)"
        )
    log.info("─" * 60)


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
    guardar(df, embeddings, equiv)
    return df, embeddings, equiv


if __name__ == "__main__":
    df, embeddings, equiv = ejecutar()
