from flask import Flask, request, jsonify, send_file
from pymongo import MongoClient
from gridfs import GridFS
from bson.objectid import ObjectId
import json

from werkzeug.utils import secure_filename
import io
import uuid

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

app = Flask(__name__)

uri = "mongodb+srv://pooniavikram348:qiVRLYNEI78dSGTl@cluster0.s6zc7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Create a new client and connect to the server
client = MongoClient(uri)

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client.flaskDB  # Database Name

# Users Collection
users = db.users       # Collection for user details
posts = db.posts       # Collection for posts
likes = db.likes       # Collection for likes


@app.route("/")
def home():
    return jsonify({"message": "Welcome to Flask based application!"})

# -------------------- User Routes --------------------
@app.route("/user/register", methods=["POST"])
def user_register():
    data = request.json  #{"email","password"}
    if users.find_one({"email": data["email"]}):
        return jsonify({"error": "User already exists"}), 400
    users.insert_one(data)
    return jsonify({"message": "User registered successfully"}), 201


@app.route("/user/login",methods=["POST"])
def user_login():
    try:
        data = request.json
        email = data.get("email", "")  # ✅ Normalize email
        password = str(data.get("password", ""))  # ✅ Convert password to string
        user=users.find_one({"email":email , "password":password})

        if user:  # ✅ Compare passwords
            return jsonify({"message": "true"}), 200

        return jsonify({"error": "User credential is incorrect"}), 400
        

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/user/profile",methods=["POST"])
def user_profile():
    data=request.json #{"email"}
    #return all posts with his email and some other datails
    return jsonify({"message":"Successfully profile send"}), 201


# -------------------- Post Routes --------------------
import json

def validate_and_fix_json(json_data):
    """
    Validates and attempts to fix malformed JSON.

    Args:
        json_data (str): The JSON string received from the request.

    Returns:
        tuple: (parsed JSON dictionary, error message or None)
    """
    try:
        data = json.loads(json_data)  # Parse JSON
        return data, None  # Return parsed data and no error
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON format: {str(e)}"  # Return error message


@app.route("/posts/create", methods=["POST"])
def post_create():
    try:
        post_Id = str(uuid.uuid4())  # Generate unique post ID

        # ✅ Get JSON Data from `form-data`
        json_data = request.form.get("json_data")
        if not json_data:
            return jsonify({"error": "Missing JSON data"}), 400

        # ✅ Parse JSON
        data, error = validate_and_fix_json(json_data)
        if error:
            return jsonify({"error": error}), 400  # Return error if JSON is invalid

        # ✅ Handle Files Correctly
        files = request.files.getlist("files")
        if not files or files[0].filename == '':
            return jsonify({"error": "No files uploaded"}), 400

        image_documents = []
        for file in files:
            filename = secure_filename(file.filename)
            image_documents.append({
                "filename": filename,
                "data": file.read()  # Save file data
            })

        # ✅ Insert into MongoDB
        data["post_Id"] = post_Id
        data["image_data"] = image_documents
        posts.insert_one(data)

        return jsonify({"message": "Post created successfully", "post_Id": post_Id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/posts/delete",methods=["POST"])
def post_delete():
    data=request.json   #{"post_Id"}
    result = posts.delete_one({"post_Id": data["post_Id"]})
    if result.deleted_count == 1:
        return jsonify({"message": "Post deleted successfully"}), 200
    else:
        return jsonify({"error": "Post not found"}), 404


@app.route("/posts/search",methods=["POST"])
def post_search():
    #search post by unique parameter  complete this
    data=request.json
    post_Id=data["post_Id"]
    result=posts.find_one({"post_Id":post_Id})
    print(result)
    return jsonify({"message":"Successfully get image"}), 201



# -------------------- Likes Routes --------------------
@app.route("/likePost", methods=["POST"])
def like_post():
    try:
        data = request.json  # Expecting {"post_Id": "...", "email": "..."}

        if not data.get("post_Id") or not data.get("email"):
            return jsonify({"error": "post_Id and email are required"}), 400

        # Check if the user has already liked this post
        if likes.find_one({"post_Id": data["post_Id"], "email": data["email"]}):
            return jsonify({"error": "Already liked the post"}), 400

        # Insert the like into the likes collection
        data["liked"] = True
        result = likes.insert_one(data)
        
        likes_count = likes.count_documents({"post_Id": data["post_Id"]})
        return jsonify({"message": likes_count}), 200
        

    except errors.ConnectionFailure:
        return jsonify({"error": "Database connection failed"}), 500  # Handle MongoDB connection failure

    except errors.WriteError:
        return jsonify({"error": "Failed to write to database"}), 500  # Handle write failures

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Catch all other unexpected errors


@app.route("/unlikePost", methods=["POST"])
def unlike_post():
    try:
        data = request.json  # Expecting {"post_Id": "...", "email": "..."}

        if not data.get("post_Id") or not data.get("email"):
            return jsonify({"error": "post_Id and email are required"}), 400

        result = likes.delete_one({"post_Id": data["post_Id"],"email":data["email"]})

        if result.deleted_count == 1:
            likes_count = likes.count_documents({"post_Id": data["post_Id"]})
            return jsonify({"message": likes_count}), 200
        else:
            return jsonify({"error": "Post not found"}), 404

    except errors.ConnectionFailure:
        return jsonify({"error": "Database connection failed"}), 500  # Handle MongoDB connection failure

    except errors.WriteError:
        return jsonify({"error": "Failed to write to database"}), 500  # Handle write failures

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Catch all other unexpected errors



if __name__ == "__main__":
    app.run(debug=True)
