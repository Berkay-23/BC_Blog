from flask import *
from wtforms import *
import email_validator
from functools import wraps
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt

# ------------------------------------------------------------------------------------------------------------------------------------------------

class RegisterForm(Form):
    
    name = StringField('İsim Soyisim')
    
    username = StringField('Kullanıcı Adı', validators=[validators.length(min=4, max=20, message='Kullanıcı adı 4-20 karakter uzunluğunda olmalıdır.')])
    
    email = EmailField('E Mail', validators=[validators.Email('Geçerli bir e-mail giriniz')])
    
    password = PasswordField('Parola', validators=[
        validators.DataRequired('Lütfen bir parola belirleyin'),
        validators.EqualTo(fieldname='confirm', message='Parolanız uyuşmuyor.')])
    
    confirm = PasswordField('Parola Doğrula', validators=[validators.DataRequired('Bu alan boş bırakılamaz')])

# ------------------------------------------------------------------------------------------------------------------------------------------------

class LoginForm(Form):
    
    username = StringField('Kullanıcı Adı', validators=[
        validators.length(min=4, max=20, message='Kullanıcı adı 4-20 karakter uzunluğunda olmalıdır.'),
        validators.DataRequired('Bu alan boş bırakılamaz')])
    
    password = PasswordField('Parola', validators=[validators.DataRequired('Bu alan boş bırakılamaz')]) 

# ------------------------------------------------------------------------------------------------------------------------------------------------

class AddArticleForm(Form):
    
    title = StringField('Başlık', validators = [validators.DataRequired(message = 'Bu alan boş bırakılamaz')])
    
    content = TextAreaField('İçerik', validators = [validators.DataRequired(message = 'Bu alan boş bırakılamaz')]) 

# ------------------------------------------------------------------------------------------------------------------------------------------------

app = Flask(__name__)

app.secret_key = 'bcblog'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'bcblog'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.route(r'/')
def index():
    return render_template('index.html')

# ------------------------------------------------------------------------------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if 'logged_in' in session:
            return f(*args, **kwargs)

        else:
            flash('Bu sayfayı görüntülemek için lütfen giriş yapın.', 'danger')
            return redirect(url_for('login'))

    return decorated_function

# ------------------------------------------------------------------------------------------------------------------------------------------------

def logout_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not('logged_in' in session):
            return f(*args, **kwargs)

        else:
            flash('Zaten < {} > hesabınızla giriş yaptınız. Başka bir hesapla giriş yapmak için çıkış yapınız.'.format(session['username']), 'danger')
            return redirect(url_for('index'))

    return decorated_function

# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.route(r'/about')
def about():
    return render_template('about.html')

# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.route(r'/register', methods = ['GET', 'POST'])
@logout_required
def register():

    form = RegisterForm(request.form)

    if request.method == 'POST' and form.validate():

        name = form.name.data
        e_mail = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        cursor.execute("""SELECT COUNT(*) AS result FROM users WHERE username = %s""", (username,))
        result = cursor.fetchone()

        if(result['result'] == 0):
            query = 'INSERT INTO users (name, email, username, password) VALUES(%s, %s, %s, %s)'
            cursor.execute(query,(name, e_mail, username, password))
            mysql.connection.commit()
            cursor.close()

            flash('Başarıyla kayıt oldunuz.', 'success')
            return redirect(url_for('login'))

        else:
            flash('Bu kullanıcı adında bir üye zaten mevcut.', 'warning')
            return render_template('register.html', form = form)

    else:
        return render_template('register.html', form = form)

# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.route(r'/login', methods = ['GET', 'POST'])
@logout_required
def login():

    form = LoginForm(request.form)

    if request.method == 'POST' and form.validate():
        username = form.username.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("""SELECT * FROM users WHERE username = %s""", (username,))
        result = cursor.fetchone()
        cursor.close()
        
        encrypted_pass = result['password']

        verify = sha256_crypt.verify(password, encrypted_pass)

        if verify:
            flash('Başarıyla giriş yaptınız.', 'success')

            session['logged_in'] = True
            session['username'] = username

            return redirect(url_for('index'))
        
        else:
            flash('Kayıt bulunamadı lütfen bilgilerinizi kontrol ediniz', 'danger')
            return render_template('login.html', form = form)

    else:
        return render_template('login.html', form = form)

# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.route(r'/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.route(r'/dashboard')
@login_required
def dashboard():
    
    cursor = mysql.connection.cursor()
    result = cursor.execute("""SELECT * FROM articles WHERE author = %s""", (session['username'],))

    if result > 0:
        articles = cursor.fetchall()
        cursor.close()
        return render_template('dashboard.html', articles = articles)

    else:
        return render_template('dashboard.html')
    

# ------------------------------------------------------------------------------------------------------------------------------------------------
@app.route(r'/addarticle', methods = ['GET', 'POST'])
@login_required
def addArticle():
    form = AddArticleForm(request.form)

    if request.method == 'POST' and form.validate():

        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        cursor.execute("""INSERT INTO articles (title, author, content) VALUES (%s, %s, %s)""", (title, session['username'], content))
        mysql.connection.commit()
        cursor.close()

        flash('Makale başarıyla eklendi', 'success')
        return redirect(url_for('dashboard'))
    else:
        return render_template('addarticle.html', form = form)

# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.route(r'/articles')
def articles():

    cursor = mysql.connection.cursor()
    result = cursor.execute("""SELECT * FROM articles""")
    
    if result > 0:
        articles = cursor.fetchall()
        cursor.close()
        return render_template('articles.html', articles = articles)
        
    else:
        return render_template('articles.html')

# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.route(r'/article/<string:id>')
def article_detail(id):

    cursor = mysql.connection.cursor()
    result = cursor.execute("""SELECT * FROM articles WHERE id = %s""", (id,))

    if result > 0:
        article = cursor.fetchone()
        cursor.close()
        return render_template('article.html', article = article)

    else:
        flash(f"{id} Numaralı makale bulunamadı", "danger")
        return redirect(url_for('articles'))
    
# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.route(r'/search', methods = ['GET', 'POST'])
def search():

    if request.method == 'GET':
        return redirect(url_for('index'))

    else:
        keyword = request.form.get('keyword')

        cursor = mysql.connection.cursor()
        result = cursor.execute(f"SELECT * FROM articles WHERE title LIKE '%{keyword}%'")

        if result > 0:
            articles = cursor.fetchall()
            cursor.close()
            return render_template('articles.html', articles = articles)

        else:
            flash(f"İçinde [{keyword}] anahtar kelimesi geçen konu başlığı bulunamadı" , "info")
            return redirect(url_for('articles'))

# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.route(r'/delete/<string:id>')
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    result = cursor.execute("""SELECT author FROM articles WHERE id = %s""", (id,))

    if result > 0:
        author = cursor.fetchone()
        
        if author['author'] == session['username']:
            cursor.execute("""DELETE FROM articles WHERE id = %s""", (id,))
            mysql.connection.commit()
            cursor.close()

            flash(f"{id} Numaralı makale başarıyla silindi.", "success")
            return redirect(url_for('dashboard'))
        
        else:
            flash(f"{id} Numaralı makale size ait değil. Bu işlem için yetkiniz yok.", "warning")
            return redirect(url_for('dashboard'))
    
    else:
        flash(f"{id} Numaralı makale bulunamadı", "danger")
        return redirect(url_for('articles'))

# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.route(r'/edit/<string:id>', methods = ['GET', 'POST'])
@login_required
def edit(id):

    if request.method == 'GET':
        cursor = mysql.connection.cursor()
        result = cursor.execute("""SELECT author FROM articles WHERE id = %s""", (id,))

        if result > 0:
            author = cursor.fetchone()

            if author['author'] == session['username']:
                cursor.execute("""SELECT * FROM articles WHERE id = %s""", (id,))
                article = cursor.fetchone()
                cursor.close()

                form = AddArticleForm()

                form.title.data = article['title']
                form.content.data = article['content']

                return render_template('edit.html', form = form, title = article['title'])
        
            else:
                flash(f"{id} Numaralı makale size ait değil. Bu işlem için yetkiniz yok.", "warning")
                return redirect(url_for('dashboard'))

        else:
            flash(f"{id} Numaralı makale bulunamadı", "danger")
            return redirect(url_for('articles'))
    
    else:
        form = AddArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        cursor = mysql.connection.cursor()
        cursor.execute("""UPDATE articles SET title = %s, content = %s WHERE id = %s""", (newTitle, newContent, id))
        mysql.connection.commit()
        cursor.close()

        flash(f"{id} Numaralı makale başarıyla güncellendi", "success")
        return redirect(url_for(f'dashboard'))


# ------------------------------------------------------------------------------------------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html')

# ------------------------------------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug = True)

# ------------------------------------------------------------------------------------------------------------------------------------------------