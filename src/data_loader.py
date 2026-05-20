import os
import glob
from config.settings import SPECIAL_DATA_DIR, GENERAL_DATA_DIR
import logging

logger = logging.getLogger(__name__)

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        logger.info(f"Loading Whisper model on {device} with {compute_type}...")
        _whisper_model = WhisperModel("small", device=device, compute_type=compute_type)
    return _whisper_model

def _do_pdf_ocr(pdf_path):
    import logging
    logger = logging.getLogger(__name__)
    try:
        import pytesseract
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path, dpi=200, last_page=15)
        text = ""
        for i, img in enumerate(images):
            try:
                page_text = pytesseract.image_to_string(img, lang='chi_tra+eng')
            except Exception:
                page_text = pytesseract.image_to_string(img)
            text += f"--- Page {i+1} ---\n{page_text}\n"
        return text
    except Exception as e:
        logger.error(f"PDF OCR failed for {pdf_path}: {e}")
        return ""

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
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            if len(text.strip()) < 15:
                logger.info(f"PDF {filepath} 似乎是掃描檔，啟動 OCR 備援機制...")
                text = _do_pdf_ocr(filepath)
            return text
        elif ext in ['jpg', 'jpeg', 'png']:
            import pytesseract
            from PIL import Image
            try:
                return pytesseract.image_to_string(Image.open(filepath), lang='chi_tra+eng')
            except Exception:
                return pytesseract.image_to_string(Image.open(filepath))
        elif ext in ['mp4', 'mp3', 'm4a', 'wav', 'flv']:
            logger.info(f"Starting Whisper transcription for {filepath}")
            model = get_whisper_model()
            segments, info = model.transcribe(filepath, beam_size=5)
            text = f"--- 語音逐字稿 (語言: {info.language}) ---\n"
            for segment in segments:
                text += f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n"
            return text

        # === Office File Parsing ===
        text = ""
        if ext == 'docx':
            import docx
            doc = docx.Document(filepath)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif ext in ['doc', 'ppt']:
            import subprocess, tempfile
            logger.info(f"Using LibreOffice to extract text from legacy {ext} file: {filepath}")
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    subprocess.run(['soffice', '--headless', '--convert-to', 'txt:Text', '--outdir', temp_dir, filepath], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    base_name = os.path.splitext(os.path.basename(filepath))[0]
                    txt_file = os.path.join(temp_dir, f"{base_name}.txt")
                    if os.path.exists(txt_file):
                        with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                            text = f.read()
            except Exception as e:
                logger.error(f"Failed to convert legacy {ext} file {filepath}: {e}")
        elif ext == 'pptx':
            from pptx import Presentation
            prs = Presentation(filepath)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"

        # Universal OCR fallback for Office files that might be purely image-based
        if ext in ['doc', 'docx', 'ppt', 'pptx'] and len(text.strip()) < 15:
            logger.info(f"{ext} 檔案 {filepath} 似乎是由純圖片組成，啟動 OCR 備援機制...")
            import subprocess, tempfile
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', temp_dir, filepath], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    base_name = os.path.splitext(os.path.basename(filepath))[0]
                    pdf_file = os.path.join(temp_dir, f"{base_name}.pdf")
                    if os.path.exists(pdf_file):
                        text = _do_pdf_ocr(pdf_file)
            except Exception as e:
                logger.error(f"Failed to run universal PDF OCR fallback for {filepath}: {e}")

        return text
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
            supported_exts = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.mp4', '.mp3', '.m4a', '.wav', '.flv']
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
                                        
                                    # 自動刪除原始佔用空間的檔案以節省硬碟容量
                                    try:
                                        os.remove(filepath)
                                        logger.info(f"[自動瘦身] 已成功刪除原始檔以釋放空間: {filepath}")
                                    except Exception as del_e:
                                        logger.warning(f"[自動瘦身] 刪除原始檔失敗 {filepath}: {del_e}")
                                        
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

