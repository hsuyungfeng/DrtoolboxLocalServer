import os
import glob
from config.settings import SPECIAL_DATA_DIR, GENERAL_DATA_DIR
import logging

logger = logging.getLogger(__name__)

def extract_text_from_file(filepath):
    ext = filepath.lower().split('.')[-1]
    try:
        if ext == 'txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        elif ext == 'pdf':
            import PyPDF2
            text = ""
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        elif ext in ['doc', 'docx']:
            import docx
            doc = docx.Document(filepath)
            return "\n".join([p.text for p in doc.paragraphs])
        elif ext in ['ppt', 'pptx']:
            from pptx import Presentation
            prs = Presentation(filepath)
            text = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
            return text
        elif ext in ['jpg', 'jpeg', 'png']:
            import pytesseract
            from PIL import Image
            try:
                # Try with traditional chinese + english
                return pytesseract.image_to_string(Image.open(filepath), lang='chi_tra+eng')
            except Exception:
                # Fallback to default if language pack is missing
                return pytesseract.image_to_string(Image.open(filepath))
        else:
            return ""
    except Exception as e:
        logger.error(f"Error extracting text from {filepath}: {e}")
        return ""

def process_and_load_directory(directory, rag_engine_instance=None, is_special=True):
    """Loads all existing .txt files immediately, then starts background OCR."""
    documents = []
    if not os.path.exists(directory):
        logger.warning(f"Directory {directory} does not exist.")
        return documents
        
    # 1. 立即載入所有已經存在的 .txt 檔案 (光速完成)
    for filepath in glob.glob(os.path.join(directory, "**/*.txt"), recursive=True):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    documents.append({"id": filepath, "content": content})
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
            
    # 2. 將尚未 OCR 的檔案放到背景慢慢處理，處理完即時塞入 RAG 引擎
    if rag_engine_instance:
        import threading
        def background_ocr():
            supported_exts = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png']
            for root, _, files in os.walk(directory):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in supported_exts:
                        filepath = os.path.join(root, file)
                        txt_path = filepath + ".txt"
                        if not os.path.exists(txt_path):
                            logger.info(f"[Background OCR] Extracting text from new file: {filepath}")
                            extracted_text = extract_text_from_file(filepath)
                            if extracted_text and extracted_text.strip():
                                try:
                                    with open(txt_path, 'w', encoding='utf-8') as f:
                                        f.write(extracted_text)
                                    # 即時更新到 RAG 記憶體
                                    doc = {"id": txt_path, "content": extracted_text}
                                    if is_special:
                                        rag_engine_instance.ingest_special_data([doc])
                                    else:
                                        rag_engine_instance.ingest_general_data([doc])
                                except Exception as e:
                                    logger.error(f"Failed to save extracted text for {filepath}: {e}")
        
        threading.Thread(target=background_ocr, daemon=True).start()
            
    return documents

def get_special_data(rag_engine_instance=None):
    logger.info(f"Loading special data from {SPECIAL_DATA_DIR}")
    docs = process_and_load_directory(SPECIAL_DATA_DIR, rag_engine_instance, is_special=True)
    
    from config.settings import PREFERRED_SPECIAL_DIR
    if PREFERRED_SPECIAL_DIR != SPECIAL_DATA_DIR:
        try:
            if os.path.exists(PREFERRED_SPECIAL_DIR):
                logger.info(f"Also loading special data from readable external path: {PREFERRED_SPECIAL_DIR}")
                external_docs = process_and_load_directory(PREFERRED_SPECIAL_DIR, rag_engine_instance, is_special=True)
                docs.extend(external_docs)
        except Exception as e:
            logger.warning(f"Could not load external special data from {PREFERRED_SPECIAL_DIR}: {e}")
            
    return docs


def get_general_data(rag_engine_instance=None):
    logger.info(f"Loading general data from {GENERAL_DATA_DIR}")
    docs = process_and_load_directory(GENERAL_DATA_DIR, rag_engine_instance, is_special=False)
    
    from config.settings import PREFERRED_GENERAL_DIR
    if PREFERRED_GENERAL_DIR != GENERAL_DATA_DIR:
        try:
            if os.path.exists(PREFERRED_GENERAL_DIR):
                logger.info(f"Also loading general data from readable external path: {PREFERRED_GENERAL_DIR}")
                external_docs = process_and_load_directory(PREFERRED_GENERAL_DIR, rag_engine_instance, is_special=False)
                docs.extend(external_docs)
        except Exception as e:
            logger.warning(f"Could not load external general data from {PREFERRED_GENERAL_DIR}: {e}")
            
    return docs

