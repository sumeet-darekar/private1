from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import desc
from models import TripStatus, db, User, Document, MasterVehicle, MasterDriver
from config import Config
import os
import json
import uuid
import logging

logging.basicConfig(level=logging.DEBUG)

# logging.getLogger('google.auth').setLevel(logging.WARNING)
# logging.getLogger('urllib3').setLevel(logging.WARNING)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

db.init_app(app)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def process_document_sample(
    project_id: str,
    location: str,
    processor_id: str,
    file_path: str,
    mime_type: str,
    document_type: str,
) -> dict:
    from google.api_core.client_options import ClientOptions
    from google.cloud import documentai_v1beta3 as documentai

    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    name = client.processor_path(project_id, location, processor_id)
    with open(file_path, "rb") as image:
        image_content = image.read()

    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)

    try:
        result = client.process_document(request=request)
        document = result.document

        # Default extracted data structure
        extracted_data = {}

        if document_type == "license":
            extracted_data = {
                "Name": None,
                "Date_of_Issue": None,
                "Expiry_Date": None,
                "DL_No": None,
            }
        elif document_type == "puc":
            extracted_data = {
                "Certificate_No": None,
                "Date_Of_Registration": None,
                "Registration_No": None,
                "Validity_Upto": None,
            }
        elif document_type == "vehicle_no":
            extracted_data = {"Vehicle_No": None}
        elif document_type == "insurance":
            extracted_data = {
                "Vehicle_Number": None,
                "Inurance_Validity_Upto": None,
            }
        elif document_type == "fc":
            extracted_data = {
                "Vehicle_Number": None,
                "FC_Validity_Upto": None,
            }

        for entity in document.entities:
            entity_name = entity.type_.lower()
            entity_value = entity.mention_text

            if document_type == "license":
                if "name" in entity_name or "Name" in entity_name:
                    extracted_data["Name"] = entity_value
                elif "issue" in entity_name or "date of issue" in entity_name:
                    extracted_data["Date_of_Issue"] = entity_value
                elif (
                    "expiry" in entity_name
                    or "expirydate" in entity_name
                    or "expiry date" in entity_name
                ):
                    extracted_data["Expiry_Date"] = entity_value
                elif "dlno" in entity_name or "license" in entity_name:
                    extracted_data["DL_No"] = entity_value

            elif document_type == "puc":
                if "certificateslno" in entity_name or "CertificateSLNo" in entity_name:
                    extracted_data["Certificate_No"] = entity_value
                elif (
                    "dateofregistration" in entity_name
                    or "DateOfRegistration" in entity_name
                ):
                    extracted_data["Date_Of_Registration"] = entity_value
                elif (
                    "registrationno" in entity_name or "registration no" in entity_name
                ):
                    extracted_data["Registration_No"] = entity_value
                elif "validityupto" in entity_name or "expiry date" in entity_name:
                    extracted_data["Validity_Upto"] = entity_value

            elif document_type == "vehicle_no":
                if "vehicleno" in entity_name or "registrationno" in entity_name:
                    extracted_data["Vehicle_No"] = entity_value

            elif document_type == "insurance":
                if "vehiclenumber" in entity_name or "Vehicle Number" in entity_name:
                    extracted_data["Vehicle_Number"] = entity_value
                elif (
                    "insurancevalidupto" in entity_name
                    or "Insurance Valid Upto" in entity_name
                ):
                    extracted_data["Inurance_Validity_Upto"] = entity_value

            elif document_type == "fc":
                if "fcnumber" in entity_name or "FCNumber" in entity_name:
                    extracted_data["FC_Number"] = entity_value
                elif "fcvalidupto" in entity_name or "FCValidUpto" in entity_name:
                    extracted_data["FC_Validity_Upto"] = entity_value

        return extracted_data
    except Exception as e:
        return {"error": str(e)}


def process_license_document(file_path: str) -> dict:
    return process_document_sample(
        project_id="275965155338",
        location="us",
        processor_id="a332667fda700f77",
        file_path=file_path,
        mime_type="image/jpeg",
        document_type="license",
    )


# Placeholder for PUC and Vehicle No processing
def process_puc_document(file_path: str) -> dict:
    # Implement PUC processing similar to process_license_document
    return process_document_sample(
        project_id="275965155338",
        location="us",
        processor_id="dcdd9dfec99cd18f",
        file_path=file_path,
        mime_type="image/jpeg",
        document_type="puc",
    )


def process_vehicle_no_document(file_path: str) -> dict:
    # Implement Vehicle No processing similar to process_license_document
    return process_document_sample(
        project_id="275965155338",
        location="us",
        processor_id="cfa207242fe794f9",
        file_path=file_path,
        mime_type="image/jpeg",
        document_type="vehicle_no",
    )


def process_insurance_document(file_path: str) -> dict:
    # Implement Vehicle No processing similar to process_license_document
    return process_document_sample(
        project_id="275965155338",
        location="us",
        processor_id="e3e54900b8c623be",
        file_path=file_path,
        mime_type="image/jpeg",
        document_type="insurance",
    )


# added code here(s)
def process_fc_document(file_path: str) -> dict:
    # Implement Vehicle No processing similar to process_license_document
    return process_document_sample(
        project_id="275965155338",
        location="us",
        processor_id="26603d288aae78ae",
        file_path=file_path,
        mime_type="image/jpeg",
        document_type="fc",
    )


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 400

    new_user = User(username=username)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()

    if user is None or not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "user_id": user.id}), 200


@app.route("/store_full_document_data", methods=["POST"])
def store_full_document_data():
    data = request.get_json()  # Get the JSON data sent in the request

    try:
        # Start a new transaction
        with db.session.no_autoflush:  # This ensures the session doesn't auto-flush before we're ready
            # Extract the necessary fields from the JSON

            # Generate a unique Trip_id starting with 'koel'
            base_trip_id = "koel"

            # Ensure the Trip_id is unique by appending a timestamp or random suffix
            import time

            unique_suffix = str(
                int(time.time())
            )  # Unix timestamp as a suffix for uniqueness
            trip_id = f"{base_trip_id}{unique_suffix}"
            driver_mobile_number = data.get("driver_mobile_number")
            vehicle_number = data.get("vehicle_number")
            vehicle_doc_remark = data.get("remarks")
            driver_license_number = data.get("driver_license_number")
            extracted_text_vehicle = data.get("extracted_text_vehicle")
            extracted_text_vehicle_json = json.dumps(extracted_text_vehicle)
            extracted_text_driver = data.get("extracted_text_driver")
            extracted_text_driver_json = json.dumps(extracted_text_driver)
            num_of_people = data.get("num_of_people")
            loading_or_unloading = data.get("loading_or_unloading")
            vehicle_type = data.get("vehicle_type")
            transporter_name = data.get("transporter_name")
            other_transporter_name = data.get("other_transporter_name")
            green_channel = data.get(
                "green_channel", False
            )  # Default to False if not provided
            vehicle_status = data.get(
                "vehicle_status", "GATE ENTRY"
            )  # Default to 'entered' if not provided
            folder_path_vehicle = data.get("folder_path_vehicle")
            folder_path_vehicle_json = json.dumps(folder_path_vehicle)
            folder_path_driver = data.get("folder_path_driver")
            folder_path_driver_json = json.dumps(folder_path_driver)

            # Check if the vehicle exists in the master_vehicle table
            vehicle = (
                db.session.query(MasterVehicle)
                .filter_by(vehicle_number=vehicle_number)
                .first()
            )

            if vehicle:
                # If the vehicle exists, update the record
                vehicle.extracted_text_vehicle = extracted_text_vehicle_json
                vehicle.folder_path_vehicle = (
                    folder_path_vehicle_json  # Update folder_path if provided
                )
                vehicle.green_channel = (
                    green_channel  # Default to False if not provided
                )
                vehicle.vehicle_doc_remark = vehicle_doc_remark
            else:
                # If the vehicle doesn't exist, create a new entry
                vehicle = MasterVehicle(
                    vehicle_number=vehicle_number,
                    extracted_text_vehicle=extracted_text_vehicle_json,
                    folder_path_vehicle=folder_path_vehicle_json,  # Add folder_path if provided
                    green_channel=green_channel,
                    vehicle_doc_remark=vehicle_doc_remark,
                )
                db.session.add(vehicle)

            # Check if the driver exists in the master_driver table
            driver = (
                db.session.query(MasterDriver)
                .filter_by(driver_license_number=driver_license_number)
                .first()
            )

            if driver:
                # If the driver exists, update the record
                driver.driver_mobile_number = driver_mobile_number
                driver.driver_vehicle_number = vehicle_number
                driver.extracted_text_driver = extracted_text_driver_json
                driver.folder_path_driver = (
                    folder_path_driver_json  # Update folder_path if provided
                )
            else:
                # If the driver doesn't exist, create a new entry
                driver = MasterDriver(
                    driver_mobile_number=driver_mobile_number,
                    driver_license_number=driver_license_number,
                    driver_vehicle_number=vehicle_number,
                    extracted_text_driver=extracted_text_driver_json,
                    folder_path_driver=folder_path_driver_json,  # Add folder_path if provided
                )
                db.session.add(driver)

            # Create a new Document object
            new_document = Document(
                Trip_id=trip_id,
                driver_mobile_number=driver_mobile_number,
                vehicle_number=vehicle_number,
                driver_license_number=driver_license_number,
                extracted_text_vehicle=extracted_text_vehicle_json,  # Use the JSON-dumped version
                extracted_text_driver=extracted_text_driver_json,  # Use the JSON-dumped version
                num_of_people=num_of_people,
                loading_or_unloading=loading_or_unloading,
                vehicle_type=vehicle_type,
                transporter_name=transporter_name,
                other_transporter_name=other_transporter_name,
                green_channel=green_channel,
                vehicle_status=vehicle_status,
                vehicle_doc_remark=vehicle_doc_remark,
            )

            # Add the new document to the session
            db.session.add(new_document)

            # Check for previous trip status to calculate duration_in
            previous_status = (
                db.session.query(TripStatus)
                .filter_by(trip_id=trip_id, vehicle_number=vehicle_number)
                .order_by(TripStatus.time.desc())
                .first()
            )

            duration_in = None
            if previous_status:
                # If there is a previous status, set the duration_in to the previous time
                duration_in = previous_status.time

            # Create a new TripStatus record
            new_trip_status = TripStatus(
                trip_id=trip_id,
                vehicle_number=vehicle_number,
                location=vehicle_status,  # Mapping vehicle_status from Document to location in TripStatus
                duration_in=duration_in,  # Use previous status time if available
            )

            # Add the new trip status to the session
            db.session.add(new_trip_status)

            # Commit the session to persist data
            db.session.commit()

            # Return a success response
            return (
                jsonify(
                    {
                        "message": "Document created successfully",
                        "document": {
                            "Trip_id": new_document.Trip_id,
                            "mobile_number": new_document.driver_mobile_number,
                            "vehicle_number": new_document.vehicle_number,
                            "driver_license_number": new_document.driver_license_number,
                            "extracted_text_vehicle": new_document.extracted_text_vehicle,
                            "extracted_text_driver": new_document.extracted_text_driver,
                            "num_of_people": new_document.num_of_people,
                            "loading_or_unloading": new_document.loading_or_unloading,
                            "vehicle_type": new_document.vehicle_type,
                            "transporter_name": new_document.transporter_name,
                            "other_transporter_name": new_document.other_transporter_name,
                            "green_channel": new_document.green_channel,
                            "vehicle_status": new_document.vehicle_status,
                            "folder_path_vehicle": vehicle.folder_path_vehicle,
                            "folder_path_driver": driver.folder_path_driver,
                            "vehicle_doc_remark": new_document.vehicle_doc_remark,
                        },
                    }
                ),
                201,
            )  # HTTP status code 201 for "Created"

    except Exception as e:
        # Rollback if there's an error and return a failure response
        db.session.rollback()
        print(str(e))
        return (
            jsonify({"message": "Failed to create document", "error": str(e)}),
            400,
        )  # HTTP status code 400 for "Bad Request"


@app.route("/search_vehicle", methods=["GET"])
def get_files():
    try:
        V_N = request.args.get(
            "V_N"
        ).upper()  # Retrieve vehicle number from query parameters

        if not V_N:
            return jsonify({"message": "vehicle number parameter is required"}), 400

        vehicle = MasterVehicle.query.filter_by(vehicle_number=V_N).first()

        if not vehicle:
            return (
                jsonify({"message": "Failed to retrieve data. / Data does not exist."}),
                404,
            )

        # Define the path for the folder corresponding to the vehicle number (V_N)
        vehicle_folder = os.path.join(app.config["UPLOAD_FOLDER"], V_N)

        # Check if the folder exists
        if not os.path.exists(vehicle_folder):
            return (
                jsonify(
                    {
                        "vehicle_details": vehicle.to_dict(),
                        "files": [],
                        "message": f"No folder or files found for vehicle number: {V_N}",
                    }
                ),
                404,
            )

        # List all files in the folder prefixed with the vehicle number (V_N)
        matching_files = [
            filename
            for filename in os.listdir(vehicle_folder)
            if filename.startswith(V_N)
        ]
        print(matching_files)

        if not matching_files:
            return (
                jsonify(
                    {
                        "vehicle_details": vehicle.to_dict(),
                        "message": f"No files found for vehicle number: {V_N}",
                    }
                ),
                404,
            )

        # Response with vehicle and files details
        return (
            jsonify({"vehicle_details": vehicle.to_dict(), "files": matching_files}),
            200,
        )

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({"message": "Internal server error", "error": str(e)}), 500
    
@app.route("/hello", methods=["GET"])
def hello():
    print("api-hit")
    return "Hello World!"

@app.route("/", methods=["GET"])
def root():
    print("api-hit")
    return "Root endpoint working!"


@app.route("/search_driver", methods=["GET"])
def search_driver():
    print("api-hit")
    # Get vehicle_number and driver_mobile_number from query parameters
    vehicle_number = request.args.get("vehicle_number").upper()
    driver_mobile_number = request.args.get("driver_mobile_number")

    # Check if both parameters are provided
    if not vehicle_number or not driver_mobile_number:
        return (
            jsonify(
                {
                    "message": "Both vehicle_number and driver_mobile_number parameters are required"
                }
            ),
            400,
        )

    # Query the MasterDriver table for the driver with the provided vehicle_number and driver_mobile_number
    driver = (
        MasterDriver.query.filter_by(
            driver_vehicle_number=vehicle_number,
            driver_mobile_number=driver_mobile_number,
        )
        .order_by(desc(MasterDriver.created_at))
        .first()
    )

    # If no driver found, return an error message
    if not driver:
        return (
            jsonify({"message": "Failed to retrieve data. / Data does not exist."}),
            404,
        )

    # Define the path for the folder corresponding to the vehicle number
    vehicle_folder = os.path.join(app.config["UPLOAD_FOLDER"], vehicle_number)

    # Check if the folder exists
    if not os.path.exists(vehicle_folder):
        return (
            jsonify(
                {
                    "driver_details": driver.to_dict(),
                    "files": [],
                    "message": f"No folder found for vehicle number: {vehicle_number}",
                }
            ),
            404,
        )

    # Check if a matching file exists in the folder
    matching_file = [
        filename
        for filename in os.listdir(vehicle_folder)
        if driver_mobile_number in filename
    ]

    # If no matching file is found, return a message indicating so
    if not matching_file:
        return (
            jsonify(
                {
                    "driver_details": driver.to_dict(),
                    "message": f"No file found for driver with license number: {driver_mobile_number}",
                }
            ),
            404,
        )

    # Response with driver details and the matching file
    return jsonify({"driver_details": driver.to_dict(), "file": matching_file}), 200


@app.route("/get_ocr_vehicle", methods=["POST"])
def get_ocr_vehicle():
    try:
        V_N = request.form.get(
            "vehicle_number"
        ).upper()  # Extract vehicle number correctly
        files = request.files
        results = {
            "filename": "",
            "1vehicle_no": "",
            "2puc": "",
            "3insurance": "",
            "4fc": "",
        }

        print(V_N)
        print(files)

        # Create a unique folder path for the current vehicle number (V_N)
        if not V_N or not files:
            return jsonify({"message": "Vehicle number or files are missing"}), 400

        # Create a unique folder path for the current vehicle number (V_N)
        vehicle_folder = os.path.join(app.config["UPLOAD_FOLDER"], V_N)

        # Create folder if it doesn't exist
        if not os.path.exists(vehicle_folder):
            os.makedirs(vehicle_folder)

        filesList = []

        # Process each file and save it in the corresponding folder
        for file_key in files:
            file = files[file_key]
            filename = f"{V_N}_{file_key}.jpg"  # Save with .jpg extension
            file_path = os.path.join(vehicle_folder, filename)
            file.save(file_path)
            filesList.append(filename)

            # Process the document based on the file_key (e.g., 'vehicle_no', 'puc', etc.)
            document_type = (
                file_key.lower().strip()
            )  # Assuming keys like 'vehicle_no', 'puc', etc.
            extracted_text = process_document(file_path, document_type)
            results[document_type] = extracted_text

        print(
            jsonify(
                {"message": "Extracted text successfully", "extractedData": results}
            )
        )
        return (
            jsonify(
                {
                    "message": "Extracted text successfully",
                    "extractedData": results,
                    "files": filesList,
                }
            ),
            200,
        )

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({"message": "Error processing request", "error": str(e)}), 500


@app.route("/get_ocr_driver", methods=["POST"])
def get_ocr_driver():
    try:
        print("api-hit")
        # Get vehicle number and driver license number from the request
        V_N = request.form.get("vehicle_number")
        D_M = request.form.get("driver_mobile_number")  # New field for license number
        license_file = request.files.get("license")  # The single license file

        results = {"filename": "", "license": ""}

        print(f"Vehicle Number: {V_N}, Driver License Number: {D_M}")
        print(license_file)

        # Ensure we have a vehicle number, driver license number, and license file
        if not V_N or not D_M or not license_file:
            return (
                jsonify(
                    {
                        "message": "Vehicle number, driver license number, and license file are required."
                    }
                ),
                400,
            )

        # Create the vehicle folder path
        vehicle_folder = os.path.join(app.config["UPLOAD_FOLDER"], V_N)

        # Check if the folder exists; if not, create it
        if not os.path.exists(vehicle_folder):
            os.makedirs(vehicle_folder)
            print(f"Created folder for vehicle {V_N}: {vehicle_folder}")

        # Define the new license file name
        new_license_filename = f"{V_N}_{D_M}_license.jpg"
        new_license_path = os.path.join(vehicle_folder, new_license_filename)

        # Check if a file with the same mobile number already exists
        existing_file = next(
            (f for f in os.listdir(vehicle_folder) if f == new_license_filename), None
        )

        # If the file exists, it will be overwritten; if not, it will be created anew
        if existing_file:
            print(
                f"Overwriting existing file for mobile number {D_M}: {new_license_path}"
            )
        else:
            print(f"Saving new file for mobile number {D_M}: {new_license_path}")

        # Save the new license file
        license_file.save(new_license_path)

        # Perform OCR or process the new license file
        extracted_text = process_document(new_license_path, "license")
        results["license"] = extracted_text
        results["filename"] = new_license_filename

        # Check if OCR extraction found any data
        if not extracted_text or all(
            value is None for value in extracted_text.values()
        ):
            # Respond with a message that data extraction was successful but no data found
            return (
                jsonify(
                    {
                        "message": "Driver license extracted but no data was found.",
                        "extractedData": results,
                        "files": new_license_filename,
                        "status": "success",
                    }
                ),
                200,
            )

        # Normal response when data is found
        print(
            jsonify(
                {
                    "message": "Driver license updated successfully",
                    "extractedData": results,
                }
            )
        )
        return (
            jsonify(
                {
                    "message": "Driver license extracted successfully",
                    "extractedData": results,
                    "files": new_license_filename,
                }
            ),
            200,
        )

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({"message": "Error processing request", "error": str(e)}), 500


from flask import request, jsonify
from sqlalchemy import desc


@app.route("/search_exit_vehicle", methods=["GET"])
def search_exit_vehicle():
    # Get the vehicle number from the query parameters
    vehicle_number = request.args.get("vehicle_number").upper()

    if not vehicle_number:
        return jsonify({"error": "Vehicle number is required"}), 400

    try:
        # Find the most recent document related to the vehicle_number (which gives us the latest trip_id)
        # Find the most recent document related to the vehicle_number (case insensitive)
        latest_document = (
            Document.query.filter(Document.vehicle_number.ilike(vehicle_number))
            .order_by(desc(Document.timestamp))
            .first()
        )

        if not latest_document:
            return jsonify({"message": "No documents found for this vehicle."}), 404

        # Get the latest trip_id from the most recent document
        latest_trip_id = latest_document.Trip_id

        # Fetch all trip status entries for the latest trip_id and vehicle_number
        latest_entries = (
            TripStatus.query.filter_by(
                trip_id=latest_trip_id, vehicle_number=vehicle_number
            )
            .order_by(TripStatus.time)
            .all()
        )

        if not latest_entries:
            return (
                jsonify({"message": "No trip status entries found for this vehicle."}),
                404,
            )

        # Prepare the response by adding all relevant trip status entries
        trip_status_list = []
        for entry in latest_entries:
            trip_status_list.append(
                {
                    "trip_id": entry.trip_id,
                    "vehicle_number": entry.vehicle_number,
                    "location": entry.location,
                    "time": entry.time.strftime("%Y-%m-%d %H:%M:%S"),
                    "remark": entry.remark,
                    "duration": entry.duration,  # calculated duration if available
                }
            )

        # Return the list of entries for the latest trip_id
        return jsonify({"latest_entries": trip_status_list}), 200

    except Exception as e:
        print("An error occurred:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/exit_vehicle", methods=["POST"])
def exit_vehicle():
    data = request.json
    vehicle_number = data.get("vehicle_number").upper()
    trip_id = data.get("trip_id")

    if not vehicle_number or not trip_id:
        return jsonify({"message": "vehicle_number and trip_id are required"}), 400

    # Check if an entry already exists for the given trip_id and location 'GATE EXIT'
    existing_entry = TripStatus.query.filter_by(
        trip_id=trip_id, location="GATE EXIT"
    ).first()

    if existing_entry:
        # Update the existing entry
        existing_entry.vehicle_number = vehicle_number
        existing_entry.time = (
            db.func.now()
        )  # Assuming you want to update the timestamp to current
        existing_entry.remark = "No Remark. Approved For Gate Exit"
        message = "Trip status updated successfully"
    else:
        # Create a new TripStatus entry
        new_entry = TripStatus(
            vehicle_number=vehicle_number,
            trip_id=trip_id,
            location="GATE EXIT",
            remark="No Remark. Approved For Gate Exit",
            time=db.func.now(),  # Set the current timestamp
        )
        db.session.add(new_entry)
        message = "New trip status added successfully"

    try:
        db.session.commit()
        return jsonify({"message": message}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": str(e)}), 500


# added here(s)
@app.route("/store-data", methods=["POST"])
def store_data():
    logging.debug("Received data: %s", request.get_json())
    # @app.route('/store-data', methods=['POST'])
    # def store_data():
    data = request.get_json()
    mobile_number = data.get("mobile_number")
    extracted_data = data.get("extracted_data")
    file_name = extracted_data.get("filename")

    # Extract new data fields
    number_of_people = data.get("number_of_people", 0)
    loading_or_unloading = data.get("loading_or_unloading", "")
    vehicle_type = data.get("vehicle_type", "")
    transporter_name = data.get("transporter_name", "")
    vehicle_number = data.get("vehicle_number", "")

    if not mobile_number or not extracted_data:
        return (
            jsonify({"message": "Mobile number and extracted data are required"}),
            400,
        )
    # if not number_of_people or not loading_or_unloading or not vehicle_type or not transporter_name:
    #     return jsonify({'message': 'All dropdown fields are required'}), 400

    try:
        # Combine extracted_data into a single JSON object
        del extracted_data["filename"]
        combined_data = json.dumps(extracted_data)

        # Create a single document entry
        document = Document(
            mobile_number=mobile_number,
            file_path=file_name,
            extracted_text=combined_data,
            num_of_people=number_of_people,
            loading_or_unloading=loading_or_unloading,
            vehicle_type=vehicle_type,
            transporter_name=transporter_name,
            # other_transporter_name=other_transporter_name,
            vehicle_number=vehicle_number,
        )

        db.session.add(document)
        db.session.commit()

        return jsonify({"message": "Data stored successfully"}), 201
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/store-data-vehicle", methods=["POST"])
def store_data_vehicle():
    logging.debug("Received data: %s", request.get_json())
    # @app.route('/store-data', methods=['POST'])
    # def store_data():
    data = request.get_json()
    extracted_data = data.get("extracted_data")
    folder_name = extracted_data.get("foldername")

    # Extract new data fields
    number_of_people = data.get("number_of_people", 0)
    loading_or_unloading = data.get("loading_or_unloading", "")
    vehicle_type = data.get("vehicle_type", "")
    transporter_name = data.get("transporter_name", "")
    vehicle_number = data.get("vehicle_number", "")
    green_channel = data.get("green_channel", "")

    if not vehicle_number or not extracted_data:
        return (
            jsonify({"message": "vehicle number and extracted data are required"}),
            400,
        )
    # if not number_of_people or not loading_or_unloading or not vehicle_type or not transporter_name:
    #     return jsonify({'message': 'All dropdown fields are required'}), 400

    try:
        # Combine extracted_data into a single JSON object
        del extracted_data["filename"]
        combined_data = json.dumps(extracted_data)

        # Create a single document entry
        masterVehicle = MasterVehicle(
            folder_path_vehicle=folder_name,
            extracted_text=combined_data,
            num_of_people=number_of_people,
            loading_or_unloading=loading_or_unloading,
            vehicle_type=vehicle_type,
            transporter_name=transporter_name,
            vehicle_number=vehicle_number,
            green_channel=green_channel,
        )

        db.session.add(masterVehicle)
        db.session.commit()

        return jsonify({"message": "Data stored successfully"}), 201
    except Exception as e:
        return jsonify({"message": str(e)}), 500


def process_document(file_path: str, document_type: str) -> dict:
    if document_type == "license":
        return process_license_document(file_path)
    elif document_type == "4fc":
        return process_fc_document(file_path)
    elif document_type == "2puc":
        return process_puc_document(file_path)
    elif document_type == "1vehicle_no":
        return process_vehicle_no_document(file_path)
    elif document_type == "3insurance":
        return process_insurance_document(file_path)
    # added here (s)
    # elif document_type == "insurance":
    #     return process_insurance_document(file_path)
    else:
        return {"error": "Unsupported document type"}


@app.route("/upload_driver_details", methods=["POST"])
def upload1():
    V_N = request.form.get("V_N")
    files = request.files   
    results = {
        "filename": "",
        "license": "",
        "vehicle_no": "",
        "puc": "",
        "insurance": "",
    }

    # Generate a single 6-digit unique identifier for the entire upload operation
    unique_id = str(uuid.uuid4().int)[:6]

    for file_key in files:
        file = files[file_key]
        filename = f"{V_N}_{file.filename}"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        document_type = (
            file_key.lower().strip()
        )  # Assuming keys are 'vehicle_no', 'license', and 'puc'
        extracted_text = process_document(file_path, document_type)
        results[document_type] = extracted_text
        if results["filename"] == "":
            results["filename"] = unique_id
    print(results)

    return jsonify(results)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0")

