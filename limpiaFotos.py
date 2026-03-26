import os
import sys

def limpiar_raws(directorio):
    EXT_FILTRO = '.jpg'
    EXT_RAW = '.cr2'
    
    if not os.path.isdir(directorio):
        print(f"Error: La ruta '{directorio}' no es un directorio válido.")
        return

    archivos = os.listdir(directorio)
    
    # Creamos un conjunto con los nombres base de los JPGs (en minúsculas)
    nombres_jpg = {
        os.path.splitext(f)[0].lower() 
        for f in archivos if f.lower().endswith(EXT_FILTRO)
    }
    
    archivos_raw = [f for f in archivos if f.lower().endswith(EXT_RAW)]
    
    print(f"--- Procesando: {os.path.abspath(directorio)} ---")
    print(f"JPGs detectados: {len(nombres_jpg)}")
    print(f"RAWs (CR2) detectados: {len(archivos_raw)}\n")

    borrados = 0
    for archivo_raw in archivos_raw:
        nombre_base_raw = os.path.splitext(archivo_raw)[0].lower()
        
        if nombre_base_raw not in nombres_jpg:
            ruta_completa = os.path.join(directorio, archivo_raw)
            try:
                # MODO SIMULACIÓN: Cambia el print por os.remove(ruta_completa) para borrar de verdad.
                print(f"[A BORRAR] {archivo_raw} (No tiene JPG correspondiente)")
                os.remove(ruta_completa) 
                borrados += 1
            except Exception as e:
                print(f"Error al intentar borrar {archivo_raw}: {e}")

    print(f"\nAcción completada. Archivos RAW huérfanos: {borrados}")

if __name__ == "__main__":
    # Verificamos si se pasó la ruta como parámetro
    if len(sys.argv) > 1:
        ruta_proporcionada = sys.argv[1]
        limpiar_raws(ruta_proporcionada)
    else:
        print("Uso: python limpiar.py <ruta_de_la_carpeta>")
        print("Ejemplo: python limpiar.py ./fotos_boda")
