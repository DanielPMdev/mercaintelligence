import os
import pandas as pd
import glob

def check_price_evolution(referencia):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_data_path = os.path.join(project_root, 'data', 'raw')
    csv_files = glob.glob(os.path.join(raw_data_path, '*.csv'))
    
    results = []
    
    for file in csv_files:
        try:
            # Load only necessary columns to speed up
            df = pd.read_csv(file, usecols=['referencia', 'precio_actual', 'precio_anterior', 'timestamp'])
            
            # Filter for the specific product
            product_data = df[df['referencia'].astype(str) == str(referencia)]
            
            if not product_data.empty:
                # Use the timestamp from the file if possible, or from the row
                # Let's take the first one found in the file for that reference
                row = product_data.iloc[0]
                results.append({
                    'timestamp': row['timestamp'],
                    'precio_actual': row['precio_actual'],
                    'precio_anterior': row['precio_anterior'],
                    'filename': os.path.basename(file)
                })
        except Exception as e:
            print(f"Error processing {file}: {e}")
            
    if not results:
        print(f"No data found for reference {referencia}")
        return
    
    # Create DataFrame and sort by timestamp
    evolution_df = pd.DataFrame(results)
    evolution_df['timestamp'] = pd.to_datetime(evolution_df['timestamp'])
    evolution_df = evolution_df.sort_values('timestamp')
    
    print(f"\nEvolución de precios para la referencia {referencia}:")
    
    # Check for changes
    evolution_df['price_changed'] = evolution_df['precio_actual'].diff().fillna(0) != 0
    
    unique_prices = evolution_df['precio_actual'].unique()
    print(f"Precios detectados: {unique_prices}")
    if len(unique_prices) > 1:
        print("\nSe detectaron cambios de precio en las siguientes fechas:")
        changes = evolution_df[evolution_df['price_changed']]
        print(changes[['timestamp', 'precio_actual', 'precio_anterior']].to_string(index=False))
    else:
        print("\nNo se detectaron cambios de precio. El precio se ha mantenido constante.")
    
    print("\nHistorial completo:")
    print(evolution_df[['timestamp', 'precio_actual', 'precio_anterior']].to_string(index=False))

if __name__ == "__main__":
    check_price_evolution(10005)
