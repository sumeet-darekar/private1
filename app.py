import os
from flask import Flask, request, jsonify
from tempfile import NamedTemporaryFile
from flask_cors import CORS
 
app = Flask(__name__)
CORS(app)
 
 
 
def process_document_sample(
    project_id: str,
    location: str,
    processor_id: str,
    file_path: str,
    mime_type: str,
) -> dict:
    from google.api_core.client_options import ClientOptions
    from google.cloud import documentai_v1beta3 as documentai
   
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
 
    name = client.processor_path(project_id, location, processor_id)
    with open(file_path, "rb") as image:
        image_content = image.read()
 
    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document
    )
 
    try:
        result = client.process_document(request=request)
        document = result.document
       
        # Default extracted data structure
        extracted_data = {}
 
        extracted_data = {
                "PO_NUMBER": None,
                "INVOICE_NUMBER": None,
                "INVOICE_DATE": None,
                "HSN_SCN": None,
                "ITEM_CODE": [],
                "ITEM_DESCRIPTION": [],
                "PART_NO": None,
                "QUANTITY": None,
                "IGST_RATE": None,
                "IGST_AMOUNT": None,
                "CGST_RATE": None,
                "CGST_AMOUNT": None,
                "SGST_RATE": None,
                "SGST_AMOUNT": None,
                "TOTAL": None,
            }
       
        for entity in document.entities:
            entity_name = entity.type_.lower()
            entity_value = entity.mention_text
            print(f"Entity found: {entity_name} - Value: {entity_value}")  # Debug log

            if "po_no" in entity_name or "buyers_order_no" in entity_name:
                extracted_data["PO_NUMBER"] = entity_value
            elif "cgst_rate" in entity_name:
                extracted_data["CGST_RATE"] = entity_value
            elif "cgst_amount" in entity_name or "csgt_amount" in entity_name:
                extracted_data["CGST_AMOUNT"] = entity_value
            elif "sgst_rate" in entity_name:
                extracted_data["SGST_RATE"] = entity_value
            elif "sgst_amount" in entity_name:
                extracted_data["SGST_AMOUNT"] = entity_value
            elif "hsn" in entity_name:
                extracted_data["HSN_SCN"] = entity_value
            elif "igst_rate" in entity_name:
                extracted_data["IGST_RATE"] = entity_value
            elif "igst_amount" in entity_name:
                extracted_data["IGST_AMOUNT"] = entity_value
            elif "invoice_no" in entity_name:
                extracted_data["INVOICE_NUMBER"] = entity_value
            elif "invoice_date" in entity_name or "dated" in entity_name:
                extracted_data["INVOICE_DATE"] = entity_value
            elif "item_code" in entity_name or "material_code" in entity_name:
                extracted_data["ITEM_CODE"].append(entity_value)  # Append to list for multiple values
            elif (
                "item_description" in entity_name
                or "material_description" in entity_name
                or "part_description" in entity_name
            ):
                extracted_data["ITEM_DESCRIPTION"].append(entity_value)  # Append to list for multiple values
            elif "part_no" in entity_name:
                extracted_data["PART_NO"] = entity_value
            elif "quantity" in entity_name:
                extracted_data["QUANTITY"] = entity_value
            elif "total" in entity_name:
                extracted_data["TOTAL"] = entity_value

       
 
        return extracted_data
    except Exception as e:
        return {"error": str(e)}
 
 
def process_invoice_document(file_path: str) -> dict:
    return process_document_sample(
        project_id="275965155338",
        location="us",
        processor_id="e7878b1968e7e278",
        file_path=file_path,
        mime_type="application/pdf",
    )
 
@app.route('/')
def hello_world():
   return 'Hello World'
 
 
 
def process_document(file_path: str) -> dict:
    return process_invoice_document(file_path)
 
@app.route('/upload', methods=['POST'])
def upload():
    # Read the raw binary data from the request body
    file_content = request.data
    
    if not file_content:
        return jsonify({"error": "No file uploaded"}), 400
    
    # Save the raw data as a temporary file
    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_content)
        temp_path = temp_file.name
    
    # Process the document using the file path
    extracted_text = process_document(temp_path)
    # print(extracted_text)
    
    # Delete the temporary file
    os.remove(temp_path)
    
    return jsonify({"extracted_text": extracted_text, "message":"okok"}), 200


@app.route('/click', methods=['POST'])
def click():
    # Read the raw binary data from the request body
    file_content = request.data
    
    if not file_content:
        return jsonify({"error": "No file uploaded"}), 400
    
    # Save the raw data as a temporary file
    temp_path = "temp_uploaded_file.pdf"
    with open(temp_path, 'wb') as temp_file:
        temp_file.write(file_content)
    
    # Return the file path and success message
    return jsonify({"file_path": temp_path, "message": "File uploaded successfully"}), 200
 
if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True, host='0.0.0.0')
