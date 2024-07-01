from flask import Flask, request, render_template, redirect, url_for, session
import json


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # This is needed for session management



with open('symptom_hierarchy.json', 'r') as f:
    symptom_hierarchy = json.load(f)


with open('Advice.json', 'r') as f:
    Advice = json.load(f)


with open('symptomName.json', 'r') as f:
    SymptomName = json.load(f)


with open('SevereSymptomsDict.json', 'r') as f:
    SevereSymptomsDict = json.load(f)


@app.route('/', methods=['GET', 'POST'])
def start_page():
    if request.method == 'POST':
        selected_category = request.form.get('category')
        if selected_category:
            return redirect(url_for('handle_category', category=selected_category))
        else:
            return render_template('start_page.html', error="Please select a category")
    else:
        top_level_keys = list(symptom_hierarchy.keys())
        return render_template('start_page.html', categories=top_level_keys, SymptomName=SymptomName)



@app.route('/category/<category>', methods=['GET', 'POST'])
def handle_category(category):
    if request.method == 'POST':
        if 'none_of_these' in request.form:
            # Redirect to page to handle non-severe symptoms
            return redirect(url_for('handle_non_severe', category=category))
        else:
            selected_symptom = request.form.get('selected_symptom')
            if selected_symptom:
                # Store the selected severe symptom and prompt for doctor consultation
                session['severe_symptom'] = selected_symptom
                session.modified = True
                return render_template('consult_doctor.html', symptom=selected_symptom, SevereSymptomsDict = SevereSymptomsDict)
            else:
                return render_template('category_page.html', category=category, error="Please select a symptom or choose 'None of these'.", SevereSymptomsDict = SevereSymptomsDict)

    else:
        subcategories = symptom_hierarchy.get(category, {})
        severe_symptoms = subcategories.get('Severe Symptom', {})
        other_keys = {key: val for key, val in subcategories.items() if key != 'Severe Symptom'}
        return render_template('category_page.html', category=category, severe_symptoms=severe_symptoms, other_keys=other_keys, SevereSymptomsDict = SevereSymptomsDict)




@app.route('/non-severe/<category>', methods=['GET', 'POST'])
def handle_non_severe(category):
    if request.method == 'POST':
        selected_subcategory = request.form.get('subcategory')
        return redirect(url_for('final_symptom', category=category, subcategory=selected_subcategory))
    
    else:
        subcategories = symptom_hierarchy.get(category, {})
        # Filter out the severe symptoms section to focus on non-severe subcategories
        non_severe_options = {key: val for key, val in subcategories.items() if key != 'Severe Symptom'}
        # Determine if a direct jump to symptom selection is needed
        direct_final = all(len(sub) == 0 for sub in non_severe_options.values())
        if direct_final:
            return redirect(url_for('final_symptom', category=category, subcategory=None))
        return render_template('non_severe.html', category=category, subcategories=non_severe_options, SymptomName=SymptomName)





@app.route('/final-symptom/<category>/', defaults={'subcategory': None}, methods=['GET', 'POST'])
@app.route('/final-symptom/<category>/<subcategory>', methods=['GET', 'POST'])
def final_symptom(category, subcategory):
    if request.method == 'POST':
        selected_symptoms = request.form.getlist('symptom')
        # Check if session list exists, if not create it
        if 'selected_symptoms_list' not in session:
            session['selected_symptoms_list'] = []

        # Update the session list with new selections, avoiding duplicates
        current_symptoms = set(session['selected_symptoms_list'])
        current_symptoms.update(selected_symptoms)
        session['selected_symptoms_list'] = list(current_symptoms)
        session.modified = True
        
        if 'continue' in request.form:
            # User clicked "Add More", so redirect to the start page without clearing the session
            return redirect(url_for('start_page'))
        else:
            # User clicked to finalize their selections, so proceed to review
            return redirect(url_for('review_selections'))
    else:
        # Fetch final symptoms for display
        final_symptoms = symptom_hierarchy[category][subcategory] if subcategory else {key: val for key, val in symptom_hierarchy[category].items() if key != 'Severe Symptom'}
        return render_template('final_symptom.html', category=category, subcategory=subcategory if subcategory else category, symptoms=final_symptoms.keys(), SymptomName=SymptomName)



@app.route('/review-selections')
def review_selections():
    # Retrieve selected symptoms from the session
    selected_symptoms = session.pop('selected_symptoms_list', [])  # This clears the symptoms from the session
    advice_accumulated = compile_advice(selected_symptoms)
    return render_template('review_selections.html', selected_symptoms=selected_symptoms, advice=advice_accumulated)



def compile_advice(symptoms):
    advice_dict = {}
    advice_set = set()  # To avoid duplication

    for symptom in symptoms:
        symptom_advice = Advice.get(symptom, {})
        for code, advices in symptom_advice.items():
            # Ensure each advice code is considered only once per session
            if code not in advice_set:
                advice_set.add(code)
                advice_dict.setdefault(symptom, {}).update({code: advices})
    return advice_dict




if __name__ == '__main__':
    app.run(debug=True)

