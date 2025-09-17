from flask import Flask, render_template, request, jsonify
import json
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get your API key from the environment variable
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

app = Flask(__name__)

# Load internship data ONCE at startup (not on every request)
def load_internships():
    try:
        with open('internships.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Successfully loaded {len(data)} internships")
        return data
    except FileNotFoundError:
        print("Error: internships.json file not found!")
        return []
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in internships.json!")
        return []

# Pre-load the internships data when the app starts
all_internships = load_internships()

# Optimized AI Recommendation Logic for larger dataset
def get_recommendations(user_data, internships):
    if not internships:
        return []
    
    recommended = []
    
    for internship in internships:
        score = 0
        reasons = []

        # Rule 1: Check for matching skills (more matches = higher score)
        skill_matches = [skill for skill in user_data['skills'] if skill in internship['required_skills']]
        if skill_matches:
            score += len(skill_matches) * 12  # 12 points per matching skill
            if len(skill_matches) > 2:
                reasons.append(f"Skills: {len(skill_matches)} matches")
            else:
                reasons.append(f"Skills: {', '.join(skill_matches)}")

        # Rule 2: Check for matching sector interest (higher weight)
        if user_data['interest'] == internship['sector']:
            score += 18  # Strong sector match bonus
            reasons.append(f"Sector: {internship['sector']}")

        # Rule 3: Check location preference
        if user_data['location'] == internship['location']:
            score += 10  # Strong location match bonus
            reasons.append("Perfect location match")
        elif user_data['location'] == 'No Preference':
            score += 4  # Small bonus for no preference
        elif user_data['location'] == 'Multiple Locations' and internship['location'] != 'Multiple Locations':
            score += 2  # Small bonus if user is flexible
        else:
            score -= 1  # Very small penalty for mismatch

        # Bonus: If internship is in high demand sectors
        high_demand_sectors = ['Technology', 'Healthcare', 'Environment']
        if internship['sector'] in high_demand_sectors:
            score += 3

        # Only suggest if the score is above meaningful threshold
        if score >= 15:  # Higher threshold to filter out weak matches
            recommended.append({
                'internship': internship,
                'score': score,
                'reasons': reasons[:2]  # Show top 2 reasons
            })

    # Sort by score (highest first) and return top 5
    recommended.sort(key=lambda x: x['score'], reverse=True)
    return recommended[:5]

# Route for the homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle form submission and show results
@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        # 1. Get the user's input from the form
        user_skills = request.form.getlist('skills')
        user_interest = request.form.get('interest')
        user_location = request.form.get('location')

        if not user_skills:
            return render_template('results.html', recommendations=[], error="Please select at least one skill.")

        user_data = {
            'skills': user_skills,
            'interest': user_interest,
            'location': user_location
        }

        # 2. Use the pre-loaded internship data
        if not all_internships:
            return render_template('results.html', recommendations=[], error="No internship data available. Please try again later.")

        # 3. Get the recommendations using our AI function
        top_recommendations = get_recommendations(user_data, all_internships)

        if not top_recommendations:
            return render_template('results.html', recommendations=[], 
                                 message="No strong matches found. Try broadening your skills or location preferences.")

        # 4. Display the results page
        return render_template('results.html', recommendations=top_recommendations)
    
    except Exception as e:
        print(f"Error in recommendation process: {e}")
        return render_template('results.html', recommendations=[], 
                             error="An error occurred while processing your request. Please try again.")

# Function to get response from Gemini API
def get_gemini_response(user_message):
    """
    Gets a response from the Gemini API using HTTP requests.
    """
    if not GEMINI_API_KEY:
        return "Error: API key not configured. Please add GEMINI_API_KEY to your .env file."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}

    prompt = {
        "contents": [{
            "parts": [{
                "text": f"""You are a helpful assistant for the PM Internship Scheme. Your ONLY purpose is to answer questions about the internships listed on the platform, the application process, required skills, or related topics. You do not answer questions about anything else. If a user asks an unrelated question, you politely decline to answer and steer the conversation back to internships.

User Question: {user_message}

Assistant Answer:"""
            }]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=prompt, timeout=10)  # Added timeout
        response.raise_for_status()
        response_data = response.json()
        
        # Extract the generated text from the response
        if 'candidates' in response_data and response_data['candidates']:
            return response_data['candidates'][0]['content']['parts'][0]['text']
        else:
            return "Sorry, I couldn't process the response correctly."
            
    except requests.exceptions.Timeout:
        return "Sorry, the request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return "Sorry, I'm having trouble connecting right now. Please try again later."
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "Sorry, an unexpected error occurred."

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

# Health check endpoint to verify data loading
@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "internships_loaded": len(all_internships),
        "message": f"Successfully loaded {len(all_internships)} internships"
    })

if __name__ == '__main__':
    # Print startup information
    print(f"Starting Flask server with {len(all_internships)} internships loaded...")
    app.run(debug=True, host='0.0.0.0')