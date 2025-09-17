from flask import Flask, render_template, request, jsonify  # Added jsonify here!
import json
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get your API key from the environment variable
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

app = Flask(__name__)

# Load internship data from the JSON file
def load_internships():
    with open('internships.json', 'r') as f:
        data = json.load(f)
    return data

# Our AI Recommendation Logic (Rule-Based Scoring)
def get_recommendations(user_data, internships):
    recommended = []
    for internship in internships:
        score = 0
        reasons = [] # List to store reasons for the match

        # Rule 1: Check for matching skills
        for skill in user_data['skills']:
            if skill in internship['required_skills']:
                score += 10 # Give 10 points for each matching skill
                reasons.append(f"Your skill: {skill}")

        # Rule 2: Check for matching sector interest
        if user_data['interest'] == internship['sector']:
            score += 8 # Give 8 points for matching sector
            reasons.append(f"Your interest: {internship['sector']}")

        # Rule 3: Check location preference
        if user_data['location'] == internship['location'] or user_data['location'] == 'No Preference':
            score += 5 # Give 5 points for matching location or no preference
            reasons.append("Matches your location preference")
        else:
            score -= 3 # Small penalty for location mismatch

        # Only suggest if the score is positive
        if score > 0 and reasons: # Ensure there is at least one reason
            # Add the internship, its score, and the reasons to the list
            recommended.append({
                'internship': internship,
                'score': score,
                'reasons': reasons[:2] # Show top 2 reasons to keep it simple
            })

    # Sort the list by score, highest first
    recommended.sort(key=lambda x: x['score'], reverse=True)
    # Return only the top 3 internships
    return recommended[:3]

# Route for the homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle form submission and show results
@app.route('/recommend', methods=['POST'])
def recommend():
    # 1. Get the user's input from the form
    user_skills = request.form.getlist('skills')
    user_interest = request.form.get('interest')
    user_location = request.form.get('location')

    user_data = {
        'skills': user_skills,
        'interest': user_interest,
        'location': user_location
    }

    # 2. Load our internship data
    all_internships = load_internships()

    # 3. Get the recommendations using our AI function
    top_recommendations = get_recommendations(user_data, all_internships)

    # 4. Display the results page
    return render_template('results.html', recommendations=top_recommendations)

# Function to get response from Gemini API - UPDATED ENDPOINT
def get_gemini_response(user_message):
    """
    Gets a response from the Gemini API using HTTP requests.
    """
    if not GEMINI_API_KEY:
        return "Error: API key not configured. Please add GEMINI_API_KEY to your .env file."

    # Try different API endpoints
    endpoints = [
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}",
        f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    ]
    
    headers = {'Content-Type': 'application/json'}

    # The structured prompt for the model
    prompt = {
        "contents": [{
            "parts": [{
                "text": f"""You are a helpful assistant for the PM Internship Scheme. Your ONLY purpose is to answer questions about the internships listed on the platform, the application process, required skills, or related topics. You do not answer questions about anything else. If a user asks an unrelated question, you politely decline to answer and steer the conversation back to internships.

User Question: {user_message}

Assistant Answer:"""
            }]
        }]
    }

    for url in endpoints:
        try:
            print(f"Trying endpoint: {url}")
            response = requests.post(url, headers=headers, json=prompt)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"Response data: {response_data}")
                
                # Extract the generated text from the response
                if 'candidates' in response_data and response_data['candidates']:
                    return response_data['candidates'][0]['content']['parts'][0]['text']
                else:
                    return "Sorry, I couldn't process the response correctly."
            
            else:
                print(f"Error response: {response.text}")
                continue  # Try next endpoint
                
        except Exception as e:
            print(f"Error with endpoint {url}: {e}")
            continue  # Try next endpoint

    # If all endpoints fail, use a fallback response
    return get_fallback_response(user_message)

def get_fallback_response(user_message):
    """
    Provides fallback responses when Gemini API is not working.
    """
    user_message_lower = user_message.lower()
    
    if 'data analysis' in user_message_lower or 'skill' in user_message_lower:
        return "Based on your data analysis skills, I recommend looking into internships like 'Healthcare Data Analysis Intern' or 'Renewable Energy Research Assistant'. These roles often require strong analytical skills. You can check the main page for specific recommendations tailored to your profile!"
    
    elif 'how' in user_message_lower or 'apply' in user_message_lower:
        return "To apply for internships, first use our recommendation tool on the main page to find matches for your skills. Then, you can apply through the official PM Internship Scheme portal once you find opportunities that interest you."
    
    elif 'location' in user_message_lower or 'where' in user_message_lower:
        return "Internships are available in various locations including Urban, Rural, and Remote areas. You can specify your location preference on the main recommendation form to find opportunities in your preferred area."
    
    elif 'requirement' in user_message_lower or 'need' in user_message_lower:
        return "Different internships have different requirements. Common requirements include skills like Data Analysis, Communication, Research, or specific software knowledge. Use the main recommendation tool to see which internships match your specific skills!"
    
    else:
        return "I'm here to help you with PM Internship Scheme questions! You can ask me about required skills, how to apply, location options, or internship requirements. For personalized recommendations, please use the main recommendation tool on our homepage."

# Route to serve the chat page
@app.route('/chat')
def chat():
    return render_template('chat.html')

# API endpoint to handle chat messages
@app.route('/chat/get_response', methods=['POST'])
def get_chat_response():
    try:
        user_message = request.json.get('message')
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # Get response from Gemini
        ai_response = get_gemini_response(user_message)
        return jsonify({"response": ai_response})
    
    except Exception as e:
        print(f"Error in chat route: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')