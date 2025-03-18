from flask import Flask, request, jsonify, send_file
from pymongo import MongoClient
from gridfs import GridFS
from bson.objectid import ObjectId
import json
import random
import smtplib
from email_validator import validate_email, EmailNotValidError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import io
import uuid

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

app = Flask(__name__)
load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))  # Example: mongodb+srv://username:password@cluster.mongodb.net/mydb
db = client[os.getenv("MONGO_DB_NAME")]  # Example: 'mydatabase'

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
total_posts= db.total_posts   #collection for post create 

otp_store = {}

# Email configuration
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")  # Sender email
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # App password or actual password

# ------------------ Utility: Send Email ---------------------
def send_email(receiver_email, otp_code):
    subject = "🔐 Your OTP Code - SetForm"
    
    # Fancy HTML Email Body
    html_body = f"""
    <html>
    <head>
      <style>
        .container {{
          width: 100%;
          padding: 20px;
          background-color: #f4f4f4;
          font-family: Arial, sans-serif;
        }}
        .content {{
          max-width: 600px;
          margin: auto;
          background: white;
          padding: 30px;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
          color: #333;
          text-align: center;
          margin-bottom: 30px;
        }}
        p {{
          font-size: 16px;
          color: #555;
          line-height: 1.6;
        }}
        .otp {{
          font-size: 28px;
          font-weight: bold;
          color: #333;
          text-align: center;
          margin: 30px 0;
          padding: 15px;
          border: 2px dashed #FF9800;
          border-radius: 8px;
          background: #FFF3E0;
        }}
        .footer {{
          margin-top: 30px;
          font-size: 14px;
          color: #777;
          text-align: center;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="content">
          <h1>CityGram Verification</h1>
          <p>Hi there,</p>
          <p>Thank you for choosing City. Please use the following One-Time Password (OTP) to complete your verification. This OTP is valid for 10 minutes.</p>
          <div class="otp">{otp_code}</div>
          <p>If you did not request this, please ignore this email.</p>
          <div class="footer">
            &copy; 2024 SetForm. All rights reserved.
          </div>
        </div>
      </div>
    </body>
    </html>
    """

    # MIME Setup
    msg = MIMEMultipart('alternative')
    msg['From'] = f"CityGram <{EMAIL_ADDRESS}>"  # ✅ Custom name "SetForm"
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # Attach both plain text and HTML parts (fallback plain text is optional)
    plain_text = f"Your OTP code is: {otp_code}\n\nThis code will expire in 10 minutes."
    msg.attach(MIMEText(plain_text, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    # Sending Email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)  # Gmail App Password
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

# ------------------ Route: Send OTP ---------------------
@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')

    # Validate email
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

    # Generate OTP
    otp_code = random.randint(100000, 999999)
    otp_store[email] = otp_code  # Store OTP temporarily (use Redis in production)
    print(f"Generated OTP for {email}: {otp_code}")  # For testing

    # Send Email
    if send_email(email, otp_code):
        return jsonify({'success': True, 'message': 'OTP sent successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to send OTP'}), 500

# ------------------ Route: Verify OTP ---------------------
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = int(data.get('otp'))

    # Check if OTP matches
    if otp_store.get(email) != otp:
        return jsonify({'success': False, 'message': 'Invalid OTP'}), 400

    # OTP verified, remove from store
    otp_store.pop(email, None)
    user = users.find_one({'email': email})
    print(user)
    if user:
        return jsonify({
            'success': True,
            'isNewUser': False,
            'email': user['email'],
        })
    else:
        return jsonify({
            'success': True,
            'isNewUser': True,
            'message': 'New user, please register',
            'email': user['email'],

        })
 

@app.route("/")
def home():
    return jsonify({"message": "Welcome to Flask based application!"})

# -------------------- User Routes --------------------
@app.route("/user/register", methods=["POST"])
def user_register():
    data = request.json  #{"email","password"}
    if users.find_one({"email": data["email"]}):
        return jsonify({"error": "User already exists"}), 400
    data["points"]=0
    users.insert_one(data)
    return jsonify({"message": "User registered successfully"}), 201


#update this api path 
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
    #send everyData except 
    result=users.find_one({"email":data["email"]})
    return jsonify({"message":result}), 201


@app.route("/user/leaderboard",methods=["POST"])
def user_leaderBoard():
    #send top 5 profiles (name ,points) based on points they earned now
    top_users = users.find({}, {"_id": 0, "name": 1, "points": 1}).sort("points", -1).limit(5)

    # Convert to a list (array)
    result = list(top_users)
    return jsonify({"message":result}),201




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
        data["solved"]=None
        data["post_Id"] = post_Id
        data["image_data"] = image_documents
        posts.insert_one(data)

        #increase points to user point table
        users.update_one({"email": data["email"]}, {"$inc": {"points": 1}})

        #add this post into toal posts table
        total_posts.insert_one({"post_Id":post_Id})

        return jsonify({"message":post_Id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/posts/delete",methods=["POST"])
def post_delete():
    data=request.json   #{"post_Id"}
    result = posts.delete_one({"post_Id": data["post_Id"]})
    if result.deleted_count == 1:
        #remove this post into toal posts table
        total_posts.delete_one({"post_Id":data["post_Id"]})
        return jsonify({"message": "Post deleted successfully"}), 200
    else:
        return jsonify({"error": "Post not found"}), 404


@app.route("/posts/search",methods=["POST"])
def post_search():
    #search post by unique parameter  complete this
    data=request.json
    post_Id=data["post_Id"]
    solved_Id=data["solved_Id"]
    result=posts.find_one({"post_Id":post_Id})
    if result:
        posts.update_one({"post_Id":post_Id},{"$set": {"solved": solved_Id}})
        return jsonify({"message":"Status Update"}),201
    else:
        return jsonify({"message":"Post does not exist"}), 400


@app.route("/post/feed", methods=["POST"])
def post_feed():
    #send all post with add of total likes count and like by him or not
    json_data = request.json

    print(json_data["email"])
    #collection of all post_Id
    post_ids = [post["post_Id"] for post in total_posts.find({}, {"post_Id": 1})]
    print(post_ids)
    # Traverse each post_id and count total likes
    result = []
    for post_id in post_ids:
        data=posts.find_one({"post_Id":post_id})
        total_likes = likes.count_documents({"post_id": post_id})  # Count likes for each post_id
        likeByHim= likes.find_one({"post_Id":post_id,"email":json_data["email"]})
        if likeByHim:
            likeByHim=True
        else:
            likeByHim=False
        data["total_likes"]=total_likes
        data["like"]=likeByHim
        result.append(data)

    print(result)
    return jsonify({"message": result}),201


# -------------------- Likes Routes --------------------
@app.route("/likePost", methods=["POST"])
def like_post():
    try:
        data = request.json  # Expecting {"post_Id": "...", "email": "..."}

        if not data.get("post_Id") or not data.get("email"):
            return jsonify({"error": "post_Id and email are required"}), 400

        # Check if the user has already liked this post
        if likes.find_one({"post_Id": data["post_Id"], "email": data["email"]}):
            #remove this
            likes.delete_one({"post_Id":data["post_Id"],"email":data["email"]})

            #decrease points to user point table
            users.update_one({"email": data["email"]}, {"$dec": {"points": 1}}) 
            return jsonify({"message": False}), 200
        else:
            #add this
            likes.insert_one({"post_Id":data["post_Id"],"email":data["email"]})

            #increase points to user point table
            users.update_one({"email": data["email"]}, {"$inc": {"points": 1}})
            
            return jsonify({"message":True}), 200
        

    except errors.ConnectionFailure:
        return jsonify({"error": "Database connection failed"}), 500  # Handle MongoDB connection failure

    except errors.WriteError:
        return jsonify({"error": "Failed to write to database"}), 500  # Handle write failures

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Catch all other unexpected errors



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)  # Accessible from LAN
