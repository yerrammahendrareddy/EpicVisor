from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from models import User, Feedback, db, Story
import spacy
from flask_migrate import Migrate
from textblob import TextBlob

nlp = spacy.load("en_core_web_sm")
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storytovideo.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db.init_app(app)

@app.route('/')
def index():
    return render_template('base.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('User registered successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('submit_story'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'user_id' not in session:
        flash('Please login first.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form['content']
        feedback = Feedback(content=content, user_id=session['user_id'])
        db.session.add(feedback)
        db.session.commit()
        flash('Feedback submitted!', 'success')
        return redirect(url_for('index'))
    return render_template('feedback.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

from spacy import displacy

@app.route('/submit_story', methods=['GET', 'POST'])
def submit_story():
    if 'user_id' not in session:
        flash('Please login first.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        story_content = request.form['story_content']
        doc = nlp(story_content)

        # Analyzing entities and nouns
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        nouns = [chunk.text for chunk in doc.noun_chunks]

        # Sentiment analysis for each sentence
        sentences = list(doc.sents)
        sentence_sentiments = {}
        for sentence in sentences:
            blob = TextBlob(sentence.text)
            sentiment_polarity = blob.sentiment.polarity
            if sentiment_polarity > 0:
                sentiment = "Positive"
            elif sentiment_polarity < 0:
                sentiment = "Negative"
            else:
                sentiment = "Neutral"
            sentence_sentiments[sentence.text] = sentiment

        overall_sentiment = "Neutral"
        avg_sentiment = sum([blob.sentiment.polarity for sentence in sentences]) / len(sentences)
        if avg_sentiment > 0:
            overall_sentiment = "Positive"
        elif avg_sentiment < 0:
            overall_sentiment = "Negative"

        new_story = Story(content=story_content, user_id=session['user_id'], sentiment=overall_sentiment)
        db.session.add(new_story)
        db.session.commit()

        flash('Story submitted successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('submit_story.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first.', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    user_stories = Story.query.filter_by(user_id=session['user_id']).all()

    last_story = user_stories[-1] if user_stories else None
    insights = {}
    if last_story:
        doc = nlp(last_story.content)

        # Manually correct entities:
        correct_entities = {
            'Bhagavad Gita': 'WORK OF ART',
            'Harivamsa': 'WORK OF ART',
            'Puranas': 'WORK OF ART'
        }

        insights['entities'] = []
        for ent in doc.ents:
            if ent.text in correct_entities:
                insights['entities'].append((ent.text, correct_entities[ent.text]))
            else:
                insights['entities'].append((ent.text, ent.label_))

        # Sentiment Analysis for sentences:
        insights['sentiments'] = []
        for sentence in doc.sents:
            blob = TextBlob(sentence.text)
            sentiment_polarity = blob.sentiment.polarity
            if sentiment_polarity > 0:
                sentiment = "Positive"
            elif sentiment_polarity < 0:
                sentiment = "Negative"
            else:
                sentiment = "Neutral"
            insights['sentiments'].append({
                'text': sentence.text,
                'sentiment': sentiment
            })

    return render_template('dashboard.html', username=user.username, insights=insights)


migrate = Migrate(app, db)








if __name__ == '__main__':
    app.run(debug=True)
