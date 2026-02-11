import sqlite3
import os

# Paths
DB_PATH = os.getenv('DB_PATH', '/app/data/encuestas.db')

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Cambiar a Groq (gratis) como predeterminado
    cursor.execute("""
        UPDATE ai_config 
        SET llm_provider = 'groq', 
            llm_model = 'llama-3.3-70b-versatile'
        WHERE id = 1
    """)
    
    conn.commit()
    print("✅ Configuración actualizada a Groq (modelo gratuito)")
    print("   Provider: groq")
    print("   Model: llama-3.3-70b-versatile")
    
    # Verificar
    cursor.execute("SELECT llm_provider, llm_model FROM ai_config WHERE id = 1")
    result = cursor.fetchone()
    print(f"\n🔍 Configuración actual: {result}")
    
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
