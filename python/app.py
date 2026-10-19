from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from Example.graph import create_graph

from pymongo import MongoClient
from bson import ObjectId

from dotenv import load_dotenv
import bcrypt
import jwt
import os
import warnings
from pathlib import Path
from datetime import datetime, timedelta

try:
    from jwt.exceptions import InsecureKeyLengthWarning
    warnings.filterwarnings("ignore", category=InsecureKeyLengthWarning)
except ImportError:
    pass
warnings.filterwarnings("ignore", message=".*HMAC key.*")

load_dotenv(Path(__file__).resolve().parent / ".env")

app = Flask(__name__)
CORS(app)

# Sprint 1 risk assessment uses an offline-trained model and a manually maintained
# CSV of student/module inputs. LMS data is intentionally not queried here.
BASE_DIR = Path(__file__).resolve().parent

MONGO_URI = os.getenv("MONGO_URI")
JWT_SECRET = os.getenv("JWT_SECRET")

# Keep MongoDB optional at startup. Risk assessment runs from local CSV/model
# files, so a MongoDB DNS or network issue should not prevent Flask from starting.
client = db = collection = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        db = client["research_db"]
        collection = db["users"]
        # Validate connectivity here; MongoClient construction can otherwise be lazy.
        client.admin.command("ping")
    except Exception as exc:
        app.logger.warning("MongoDB unavailable; database-backed routes are disabled: %s", exc)
        if client is not None:
            client.close()
        client = db = collection = None

@app.route("/", methods=["GET"])
def home():
    return "Flask server is running"


@app.route("/api/auth/login", methods=["POST"])
def login():

    if collection is None or not JWT_SECRET:
        return jsonify({"message": "Authentication requires MONGO_URI and JWT_SECRET in python/.env"}), 503

    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "message": "Email and password are required"
        }), 400

    user = collection.find_one({
        "email": email
    })

    if not user:
        return jsonify({
            "message": "Invalid email or password"
        }), 401

    if not bcrypt.checkpw(
        password.encode("utf-8"),
        user["password"].encode("utf-8")
    ):
        return jsonify({
            "message": "Invalid email or password"
        }), 401

    token = jwt.encode(
        {
            "user_id": str(user["_id"]),
            "user": {
                "id": str(user["_id"]),
                "role": user.get("role", "Student")
            },
            "email": user["email"],
            "exp": datetime.utcnow() + timedelta(hours=24)
        },
        JWT_SECRET,
        algorithm="HS256"
    )

    return jsonify({
        "token": token,
        "user": {
            "_id": str(user["_id"]),
            "id": str(user["_id"]),
            "name": user.get("name"),
            "email": user.get("email"),
            "role": user.get("role")
        }
    }), 200

@app.route("/api/auth/me", methods=["GET"])
def get_current_user():

    if collection is None or not JWT_SECRET:
        return jsonify({"message": "Authentication requires MONGO_URI and JWT_SECRET in python/.env"}), 503

    token = request.headers.get("x-auth-token")

    if not token:
        return jsonify({
            "message": "No token provided"
        }), 401

    try:
        decoded = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"]
        )

        user_id = decoded.get("user_id")
        if not user_id and isinstance(decoded.get("user"), dict):
            user_id = decoded["user"].get("id") or decoded["user"].get("_id")
        if not user_id:
            user_id = decoded.get("id") or decoded.get("sub")

        user = None
        if user_id:
            try:
                user = collection.find_one({"_id": ObjectId(user_id)})
            except Exception:
                user = collection.find_one({"_id": user_id})

        if not user and decoded.get("email"):
            user = collection.find_one({"email": decoded["email"]})

        if not user:
            return jsonify({
                "message": "User not found"
            }), 404

        return jsonify({
            "_id": str(user["_id"]),
            "id": str(user["_id"]),
            "name": user.get("name"),
            "email": user.get("email"),
            "role": user.get("role")
        }), 200

    except jwt.ExpiredSignatureError:
        return jsonify({
            "message": "Token expired"
        }), 401

    except jwt.InvalidTokenError:
        return jsonify({
            "message": "Invalid token"
        }), 401
    except Exception as exc:
        app.logger.exception("Failed to get current user")
        return jsonify({
            "message": "Failed to authenticate user",
            "error": str(exc)
        }), 500

@app.route("/api/auth/register", methods=["POST", "OPTIONS"])
def register():

    if collection is None or not JWT_SECRET:
        return jsonify({"message": "Authentication requires MONGO_URI and JWT_SECRET in python/.env"}), 503

    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({
            "message": "Name, email and password are required"
        }), 400

    existing_user = collection.find_one({
        "email": email
    })

    if existing_user:
        return jsonify({
            "message": "User already exists"
        }), 400

    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    user = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "role": "Student",
        "createdAt": datetime.utcnow()
    }

    result = collection.insert_one(user)

    token = jwt.encode(
        {
            "user_id": str(result.inserted_id),
            "user": {
                "id": str(result.inserted_id),
                "role": "Student"
            },
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=24)
        },
        JWT_SECRET,
        algorithm="HS256"
    )

    return jsonify({
        "message": "Registration successful",
        "token": token,
        "user": {
            "_id": str(result.inserted_id),
            "id": str(result.inserted_id),
            "name": name,
            "email": email,
            "role": "Student"
        }
    }), 201



@app.route("/graph", methods=["POST"])
def graph():
    data = request.get_json()

    student_id = data.get("studentId")

    image = create_graph(student_id)

    return send_file(
        image,
        mimetype="image/png"
    )

@app.route("/Example/new", methods=["GET"])
def example_data():
    try:
        if collection is None:
            return jsonify({"error": "MongoDB is unavailable or MONGO_URI is not configured"}), 503
        data = list(collection.find({}, {"_id": 0, "password": 0}))
        for user in data:
            if "createdAt" in user:
                user["createdAt"] = str(user["createdAt"])

        return jsonify(data), 200

    except Exception as e:
        print("Error fetching example data:", e)
        return jsonify({
            "error": "Failed to fetch data",
            "message": str(e)
        }), 500


@app.route("/api/risk-assessment", methods=["GET"])
def risk_assessment():
    """Return at-risk modules assigned to the authenticated user only."""
    token = request.headers.get("x-auth-token")
    if not token:
        return jsonify({"error": "Sign in to view your risk assessment."}), 401
    if not JWT_SECRET:
        return jsonify({"error": "JWT_SECRET is not configured for the Python service."}), 503

    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = (decoded.get("user") or {}).get("id") or decoded.get("user_id")
        if not user_id:
            return jsonify({"error": "The login token does not contain a user ID. Sign out and sign in again."}), 401

        from RiskAssessment.model import assess_manual_records

        assessments = assess_manual_records(str(user_id))
        return jsonify({"assessments": assessments, "count": len(assessments), "user_id": str(user_id)}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Your session has expired. Sign in again."}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Your login token is invalid. Sign in again."}), 401
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("Risk assessment failed")
        return jsonify({"error": "Risk assessment failed", "message": str(exc)}), 500



if __name__ == "__main__":
    from RiskAssessment.model import train_model

    try:
        _, training_info = train_model()
        acc = training_info.get("accuracy")
        acc_str = f", accuracy: {acc:.1%}" if acc is not None else ""
        print(f"Risk model trained from {training_info['training_rows']} rows ({training_info['classes']} risk levels{acc_str}).")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Risk model was not trained: {exc}")
    app.run(port=3000, debug=False)
