from flask import Flask, render_template, url_for, request, redirect
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash
import os
from datetime import datetime

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.secret_key = 'secret_key'
login_manager = LoginManager(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db, command='migrate')
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    favorites = db.relationship('Favorite', backref='user', lazy=True)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tags = db.Column(db.String(100), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    favorites = db.relationship('Favorite', backref='recipe', lazy=True)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)

    def get_recipe_name(self):
        return self.recipe.name

    def get_recipe_tags(self):
        return self.recipe.tags

    def get_recipe_id(self):
        return self.recipe.id

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
@app.route('/home')
def index():
    return render_template('index.html')


@app.route('/recipe/<int:id>')
def recipe(id):
    recipe = Recipe.query.get(id)
    user = User.query.get(recipe.author_id)
    is_favorite = Favorite.query.filter_by(user_id=current_user.id, recipe_id=id).first() is not None if current_user.is_authenticated else False
    return render_template('recipe.html', recipe=recipe, author_username=user.username, is_favorite=is_favorite)


@app.route('/add-recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    if request.method == 'POST':
        recipe_name = request.form.get('recipe_name')
        recipe_description = request.form.get('recipe_description')
        recipe_ingredients = request.form.get('recipe_ingredients')
        recipe_instructions = request.form.get('recipe_instructions')

        recipe = Recipe()
        recipe.name = recipe_name
        recipe.tags = recipe_description
        recipe.ingredients = recipe_ingredients
        recipe.instructions = recipe_instructions
        recipe.author_id = current_user.id

        db.session.add(recipe)
        db.session.commit()
        return redirect('/my-recipes')

    return render_template('add-recipe.html')


@app.route('/profile')
@login_required
def profile():
    if current_user.is_authenticated:
        username = current_user.username
        date = current_user.registration_date
        return render_template('profile.html', username=username, date=date)
    return render_template('login.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect('/home')

    return render_template('login.html')



@app.route('/registration', methods=['POST', 'GET'])
def registration():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User(username=username)
        user.set_password(password)
        user.registration_date = datetime.utcnow()

        db.session.add(user)
        db.session.commit()

        return redirect(url_for('profile'))
    return render_template('registration.html')


@app.route('/add-to-favorites/<int:recipe_id>', methods=['POST'])
@login_required
def add_to_favorites(recipe_id):
    recipe = Recipe.query.get(recipe_id)
    favorite = Favorite.query.filter_by(user_id=current_user.id, recipe_id=recipe.id).first()
    if not favorite:
        favorite = Favorite(user_id=current_user.id, recipe_id=recipe.id)
        db.session.add(favorite)
        db.session.commit()

    return redirect(url_for('recipe', id=recipe_id))

@app.route('/favorite')
@login_required
def favorite():
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    favorite_recipes = []
    for favorite in favorites:
        recipe_name = favorite.get_recipe_name()
        recipe_tags = favorite.get_recipe_tags()
        recipe_id = favorite.get_recipe_id()
        favorite_recipes.append({'name': recipe_name, 'tags': recipe_tags, 'id': recipe_id})
    return render_template('favorite.html', favorite_recipes=favorite_recipes)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    if query:
        recipes = Recipe.query.filter(
            (Recipe.name.ilike(f'%{query}%')) | (Recipe.tags.ilike(f'%{query}%'))
        ).all()
    else:
        recipes = []
    return render_template('search_results.html', recipes=recipes)

@app.route('/search_results')
def search_results():
    return render_template('search_results.html')

@app.route('/recipes')
def recipes():
    recipes = Recipe.query.all()
    return render_template('recipes.html', recipes=recipes)

@app.route('/my-recipes')
@login_required
def my_recipes():
    my_recipes = Recipe.query.filter_by(author_id=current_user.id).all()
    return render_template('my_recipes.html', my_recipes=my_recipes)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)



