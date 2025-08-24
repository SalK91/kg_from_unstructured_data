# Building a Knowledge Graph (KG) from Unstructured Text with LLMs  

This tutorial shows how to generate a **Knowledge Graph (KG)** from unstructured text using a Large Language Model (LLM) and Neo4j.  

## Steps  

### 1. Create a Neo4j Sandbox  
- Go to [Neo4j Sandbox](https://sandbox.neo4j.com/)  
- Create a **blank project** (no sample dataset).  

### 2. Set Up LLM API  
- Sign up for [Cohere](https://cohere.com/) (free tier).  
- Get your API key.  

## Create you Env file with 
COHERE_API_KEY
NEO4J_URI
NEO4J_USER
NEO4J_PASSWORD

### 3. Prepare Text Data  
- Choose any unstructured text  

### 4. Prompt the LLM for Entities & Relationships  
Craft a prompt that asks the LLM to extract **entities (nodes)** and **relationships (edges)**.  

**Example Prompt:**  
```text
Extract entities and their relationships from the following text.  
Return output as JSON with fields: {entities: [...], relationships: [...]}  
```

### 5. Create Nodes & Relationships in Neo4j
See function that takes LLM output and creates nodes and relationships.