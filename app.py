from flask import Flask, render_template, request
import json

app = Flask(__name__)

# Load our fake internship data
with open('internships.json', 'r') as f:
    all_internships = json.load(f)

@app.route('/')
def index():
    # This just renders the initial form page
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    # 1. Get user input from the form
    user_skills = request.form.getlist('skills') # Gets list of checked skills
    user_interests = request.form.getlist('interests')
    user_location = request.form.get('location')

    recommendations = []
    reasons = []

    # 2. THE RULE-BASED AI LOGIC
    for internship in all_internships:
        score = 0
        reason = []

        # Rule 1: Check matching skills
        for skill in user_skills:
            if skill in internship['required_skills']:
                score += 10
                reason.append(f"skill {skill}")

        # Rule 2: Check matching sector interest
        for interest in user_interests:
            if interest == internship['sector']:
                score += 8
                reason.append(f"interest in {interest}")

        # Rule 3: Check location preference
        if user_location == internship['location'] or user_location == "No Preference":
            score += 5
            reason.append("location preference")
        else:
            score -= 3 # Penalize mismatched location

        # If the internship scored points, add it to our list
        if score > 0:
            recommendations.append((internship, score, ", ".join(reason)))

    # 3. Sort the list by score (highest first) and pick top 3
    recommendations.sort(key=lambda x: x[1], reverse=True)
    top_recommendations = recommendations[:3]

    # 4. Send the results to the template for display
    return render_template('results.html', recommendations=top_recommendations)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')