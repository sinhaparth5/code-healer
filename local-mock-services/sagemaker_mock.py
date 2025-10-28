"""
Mock SageMaker service for local testing
Provides LLM and Embedding endpoints
"""

from flask import Flask, request, jsonify
import numpy as np
import time
import logging
from threading import Thread
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import sentence_transformers, but don't fail if it's not available
embedding_model = None
USE_REAL_EMBEDDINGS = False

def load_embedding_model():
    global embedding_model, USE_REAL_EMBEDDINGS
    try:
        logger.info("Attempting to load embedding model...")
        from sentence_transformers import SentenceTransformer
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        USE_REAL_EMBEDDINGS = True
        logger.info("Embedding model loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load sentence_transformers: {e}")
        logger.info("Will use mock embeddings instead")
        USE_REAL_EMBEDDINGS = False

# LLM App
llm_app = Flask('llm-endpoint')

@llm_app.route('/health', methods=['GET'])
def llm_health():
    return jsonify({"status": "healthy", "service": "llm"}), 200

@llm_app.route('/invocations', methods=['POST'])
def llm_invocations():
    """Mock LLM endpoint - mimics SageMaker LLM inference"""
    try:
        start_time = time.time()
        data = request.get_json()
        
        # Extract prompt
        prompt = data.get('inputs', data.get('prompt', ''))
        max_tokens = data.get('parameters', {}).get('max_new_tokens', 512)
        
        logger.info(f"LLM inference request - prompt length: {len(prompt)}")
        
        # Simulate processing time
        time.sleep(0.1)
        
        # Generate mock response based on prompt content
        if 'error' in prompt.lower() or 'fix' in prompt.lower():
            generated_text = """Based on the error analysis, here's the recommended fix:

1. **Root Cause**: The service is experiencing timeout issues due to database connection pool exhaustion.

2. **Recommended Actions**:
   - Increase database connection pool size from 10 to 20
   - Add connection timeout of 30 seconds
   - Implement connection retry logic with exponential backoff

3. **Code Changes**:
```python
# Update database configuration
DB_CONFIG = {
    'pool_size': 20,
    'max_overflow': 10,
    'pool_timeout': 30,
    'pool_recycle': 3600
}
```

4. **Confidence**: 0.87
5. **Risk Level**: Medium
"""
        else:
            generated_text = f"Mock LLM response for: {prompt[:100]}..."
        
        latency = time.time() - start_time
        
        response = {
            "generated_text": generated_text,
            "model": "mock-llama-3.1-8b",
            "latency_ms": round(latency * 1000, 2),
            "tokens_generated": len(generated_text.split())
        }
        
        logger.info(f"LLM inference completed in {latency:.2f}s")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"LLM inference error: {e}")
        return jsonify({"error": str(e)}), 500

# Embedding App
embedding_app = Flask('embedding-endpoint')

@embedding_app.route('/health', methods=['GET'])
def embedding_health():
    return jsonify({"status": "healthy", "service": "embedding"}), 200

@embedding_app.route('/invocations', methods=['POST'])
def embedding_invocations():
    """Mock embedding endpoint - mimics SageMaker embedding inference"""
    try:
        start_time = time.time()
        data = request.get_json()
        
        # Extract text to embed
        texts = data.get('inputs', data.get('text', []))
        if isinstance(texts, str):
            texts = [texts]
        
        logger.info(f"Embedding request - {len(texts)} texts")
        
        # Generate embeddings
        if USE_REAL_EMBEDDINGS and embedding_model:
            embeddings = embedding_model.encode(texts).tolist()
        else:
            # Use deterministic mock embeddings based on text hash
            # This ensures consistent embeddings for the same text
            embeddings = []
            for text in texts:
                # Create a deterministic "embedding" based on text hash
                np.random.seed(hash(text) % (2**32))
                embedding = np.random.rand(384).tolist()
                embeddings.append(embedding)
        
        latency = time.time() - start_time
        
        response = {
            "embeddings": embeddings,
            "model": "mock-all-MiniLM-L6-v2" if not USE_REAL_EMBEDDINGS else "all-MiniLM-L6-v2",
            "dimension": len(embeddings[0]) if embeddings else 0,
            "latency_ms": round(latency * 1000, 2),
            "using_real_model": USE_REAL_EMBEDDINGS
        }
        
        logger.info(f"Embedding completed in {latency:.2f}s (real_model={USE_REAL_EMBEDDINGS})")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return jsonify({"error": str(e)}), 500

def run_llm_server():
    """Run LLM server on port 8080"""
    llm_app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

def run_embedding_server():
    """Run embedding server on port 8081"""
    embedding_app.run(host='0.0.0.0', port=8081, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Load embedding model in background
    Thread(target=load_embedding_model, daemon=True).start()
    
    # Start both servers
    llm_thread = Thread(target=run_llm_server, daemon=True)
    embedding_thread = Thread(target=run_embedding_server, daemon=True)
    
    llm_thread.start()
    embedding_thread.start()
    
    logger.info("Mock SageMaker services started")
    logger.info("LLM endpoint: http://0.0.0.0:8080")
    logger.info("Embedding endpoint: http://0.0.0.0:8081")
    
    # Keep main thread alive
    llm_thread.join()
    embedding_thread.join()