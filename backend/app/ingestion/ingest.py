import os, glob
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import TokenTextSplitter
#from langchain_text_splitters import SemanticChunker, TokenTextSplitter
#from langchain_postgres.vectorstores import PGVector as PGVectorStore
#from langchain_postgres import ConnectionParams
from langchain_community.vectorstores.pgvector import PGVector as PGVectorStore

load_dotenv()

# --- Config pulled from .env ---
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

#db connection
PG_CONN_STR = (
    f"postgresql+psycopg://{os.getenv('PGUSER','postgres')}:"
    f"{os.getenv('PGPASSWORD','postgres')}@"
    f"{os.getenv('PGHOST','localhost')}:"
    f"{os.getenv('PGPORT','5432')}/"
    f"{os.getenv('PGDATABASE','seattle_rag')}"
)
COLLECTION = os.getenv("PGVECTOR_COLLECTION", "seattle_docs")

#conn = ConnectionParams.from_connection_string(PG_CONN_STR)

#extract the text from the pdfs
def pdf_load_text(path):
    reader = PdfReader(path)
    extracted_pages = []

    for i, page in  enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            extracted_pages.append({"page": i, "text":text})
    return extracted_pages


#chunking function - semantically 
def chunk_pages_semantic(pages):

    emb = OpenAIEmbeddings(model = "text-embedding-3-small")

    semantic = SemanticChunker(emb, breakpoint_threshold_type = "percentile",
                               breakpoint_threshold_amount=95)
    
    token_cap = TokenTextSplitter(chunk_size=800, chunk_overlap =120,encoding_name="cl100k_base")

    chunks = []

    for p in pages:
        parts = semantic.split_text(p["text"])

        for part in parts:
            for capped in token_cap.split_text(part):
                chunks.append({"content":capped, "metadata":{"page":p["page"]}})

    return chunks


#ingestion pipeline
def main():
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

    pdfs = glob.glob("docs/raw/*.pdf")
    if not pdfs:
        print("No PDFs found in docs/raw. Add files and re-run.")
        return
    
    texts, metas = [],[]
    for pdf in pdfs:
        title = os.path.basename(pdf)
        pages = pdf_load_text(pdf)
        chunks = chunk_pages_semantic(pages)

        for ch in chunks:
            texts.append(ch["content"])
            metas.append({"source": title, "page": ch["metadata"]["page"]})


    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    #vstore = PGVectorStore( connection = conn, collection_name=COLLECTION,
#                           embedding_function=embeddings)

    vstore = PGVectorStore.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metas,
        connection_string=PG_CONN_STR,
        collection_name=COLLECTION
    )
     
    #vstore.add_texts(texts,metadatas=metas)

    print(f"Ingested {len(texts)} chunks into '{COLLECTION}'")



if __name__ == "__main__":
    main()