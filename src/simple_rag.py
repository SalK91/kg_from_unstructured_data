from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
import os

# ----- 1. Create embeddings -----
def create_embeddings(documents, model_name='all-MiniLM-L6-v2'):
    """
    documents: list of strings
    returns: numpy array of embeddings, and the model
    """
    model = SentenceTransformer(model_name)
    embeddings = model.encode(documents, show_progress_bar=True)
    return embeddings, model


# ----- 2. Create FAISS database -----
def create_faiss_index(embeddings):
    """
    embeddings: numpy array of shape (n_docs, dim)
    returns: FAISS index
    """
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings, dtype="float32"))
    return index


# ----- 3. Retrieve relevant chunks -----
def retrieve_chunks(query, index, documents, model, top_k=3):
    """
    query: string
    index: FAISS index
    documents: list of strings
    model: SentenceTransformer model used for embeddings
    top_k: number of similar chunks to retrieve
    returns: list of top-k chunk texts
    """
    q_embed = model.encode([query])  # batch format
    D, I = index.search(np.array(q_embed, dtype="float32"), top_k)
    return [documents[i] for i in I[0]]

def save_artifacts(embeddings, index, documents, path="artifacts", prefix="mydata"):
    """
    Save embeddings, FAISS index, and documents to disk.
    """
    os.makedirs(path, exist_ok=True)  # ensure folder exists

    # Save embeddings
    np.save(os.path.join(path, f"{prefix}_embeddings.npy"), embeddings)

    # Save FAISS index
    faiss.write_index(index, os.path.join(path, f"{prefix}_faiss.index"))

    # Save documents (list of strings)
    with open(os.path.join(path, f"{prefix}_documents.pkl"), "wb") as f:
        pickle.dump(documents, f)

def load_artifacts(path="artifacts", prefix="mydata"):
    """
    Load embeddings, FAISS index, and documents from disk.
    """
    embeddings = np.load(os.path.join(path, f"{prefix}_embeddings.npy"))

    index = faiss.read_index(os.path.join(path, f"{prefix}_faiss.index"))

    with open(os.path.join(path, f"{prefix}_documents.pkl"), "rb") as f:
        documents = pickle.load(f)

    return embeddings, index, documents
