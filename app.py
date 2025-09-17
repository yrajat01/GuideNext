from flask import Flask, render_template, request
import json

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') # Run the server
