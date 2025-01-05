from flask import Flask, render_template, request, jsonify
from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime
import os
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Liste des emplacements locaux
LOCAL_LOCATIONS = ['Strasbourg', 'Alsace', 'Grand Est', '67000']

def is_local_job(job_location):
    if not job_location:
        return False
    return any(location.lower() in job_location.lower() for location in LOCAL_LOCATIONS)

def scrape_linkedin_jobs():
    jobs = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # URL de recherche LinkedIn avec paramètres de localisation
            url = "https://www.linkedin.com/jobs/search/?keywords=designer&location=Strasbourg%2C%20Grand%20Est%2C%20France&distance=25"
            page.goto(url)
            
            job_cards = page.query_selector_all(".job-card-container")
            
            for card in job_cards:
                try:
                    title = card.query_selector('.job-card-list__title')
                    company = card.query_selector('.job-card-container__company-name')
                    location = card.query_selector('.job-card-container__metadata-item')
                    link = card.query_selector('.job-card-list__title')
                    
                    job = {
                        'title': title.inner_text() if title else 'N/A',
                        'company': company.inner_text().strip() if company else 'N/A',
                        'location': location.inner_text() if location else 'N/A',
                        'link': link.get_attribute('href') if link else 'N/A',
                        'source': 'LinkedIn',
                        'date_added': datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    if is_local_job(job['location']):
                        jobs.append(job)
                except Exception as e:
                    logger.error(f"Erreur lors du scraping d'une offre LinkedIn: {str(e)}")
            
            browser.close()
    except Exception as e:
        logger.error(f"Erreur lors du scraping LinkedIn: {str(e)}")
    return jobs

def scrape_indeed_jobs():
    jobs = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # URL Indeed avec paramètres de localisation
            url = "https://fr.indeed.com/jobs?q=designer&l=Strasbourg%20(67)&radius=25"
            page.goto(url)
            
            job_cards = page.query_selector_all(".job_seen_beacon")
            
            for card in job_cards:
                try:
                    title = card.query_selector('[class*="jobTitle"]')
                    company = card.query_selector('[class*="companyName"]')
                    location = card.query_selector('[class*="companyLocation"]')
                    
                    job = {
                        'title': title.inner_text() if title else 'N/A',
                        'company': company.inner_text() if company else 'N/A',
                        'location': location.inner_text() if location else 'N/A',
                        'link': 'https://fr.indeed.com' + card.get_attribute('href') if card.get_attribute('href') else 'N/A',
                        'source': 'Indeed',
                        'date_added': datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    if is_local_job(job['location']):
                        jobs.append(job)
                except Exception as e:
                    logger.error(f"Erreur lors du scraping d'une offre Indeed: {str(e)}")
            
            browser.close()
    except Exception as e:
        logger.error(f"Erreur lors du scraping Indeed: {str(e)}")
    return jobs

def scrape_apec_jobs():
    jobs = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # URL APEC avec paramètres de localisation
            url = "https://www.apec.fr/candidat/recherche-emploi.html/emploi?motsCles=designer&localisation=Strasbourg%2067000&distance=25"
            page.goto(url)
            
            job_cards = page.query_selector_all(".card-offer")
            
            for card in job_cards:
                try:
                    title = card.query_selector('.card-title')
                    company = card.query_selector('.card-offer__company')
                    location = card.query_selector('.card-offer__location')
                    link = card.query_selector('a')
                    
                    job = {
                        'title': title.inner_text() if title else 'N/A',
                        'company': company.inner_text() if company else 'N/A',
                        'location': location.inner_text() if location else 'N/A',
                        'link': 'https://www.apec.fr' + link.get_attribute('href') if link else 'N/A',
                        'source': 'APEC',
                        'date_added': datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    if is_local_job(job['location']):
                        jobs.append(job)
                except Exception as e:
                    logger.error(f"Erreur lors du scraping d'une offre APEC: {str(e)}")
            
            browser.close()
    except Exception as e:
        logger.error(f"Erreur lors du scraping APEC: {str(e)}")
    return jobs

def scrape_jobs():
    """Fonction principale de scraping qui combine toutes les sources"""
    all_jobs = []
    all_jobs.extend(scrape_linkedin_jobs())
    all_jobs.extend(scrape_indeed_jobs())
    all_jobs.extend(scrape_apec_jobs())
    
    # Sauvegarder dans un fichier CSV
    df = pd.DataFrame(all_jobs)
    df.to_csv('jobs.csv', index=False)
    logger.info(f"Scraping terminé : {len(all_jobs)} offres trouvées")
    return all_jobs

def send_email_notification(new_jobs):
    """Envoie un email avec les nouvelles offres d'emploi"""
    if not new_jobs:
        return
    
    sender_email = os.getenv('EMAIL_USER')
    sender_password = os.getenv('EMAIL_PASSWORD')
    receiver_email = os.getenv('NOTIFICATION_EMAIL')
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"Nouvelles offres d'emploi ({len(new_jobs)} offres trouvées)"
    
    body = "Nouvelles offres d'emploi :\n\n"
    for job in new_jobs:
        body += f"Titre: {job['title']}\n"
        body += f"Entreprise: {job['company']}\n"
        body += f"Lieu: {job['location']}\n"
        body += f"Lien: {job['link']}\n"
        body += "------------------------\n"
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        logger.info("Email de notification envoyé avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email: {str(e)}")

def init_scheduler():
    """Initialise le planificateur de tâches"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=scrape_jobs, trigger="interval", hours=12)
    scheduler.start()
    logger.info("Planificateur initialisé")

@app.route('/')
def index():
    """Page principale"""
    jobs = []
    if os.path.exists('jobs.csv'):
        jobs = pd.read_csv('jobs.csv').to_dict('records')
    return render_template('index.html', jobs=jobs)

@app.route('/trigger-scraping')
def trigger_scraping():
    """Route pour déclencher le scraping manuellement"""
    try:
        jobs = scrape_jobs()
        return f"Scraping terminé avec succès. {len(jobs)} offres trouvées."
    except Exception as e:
        return f"Erreur lors du scraping: {str(e)}", 500

if __name__ == '__main__':
    init_scheduler()
    app.run(host='0.0.0.0', debug=True)import os
    import sys
    import subprocess
    
    # 1. Créer le dossier templates s'il n'existe pas
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # 2. Créer le fichier index.html
    template_content = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>JobSearch Designer</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h1>JobSearch Designer</h1>
            
            <div class="row mt-4">
                <div class="col-md-4">
                    <h2>Mon Profil</h2>
                    <form method="POST" action="/upload" enctype="multipart/form-data">
                        <div class="mb-3">
                            <label class="form-label">CV</label>
                            <input type="file" class="form-control" name="cv">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Portfolio</label>
                            <input type="file" class="form-control" name="portfolio">
                        </div>
                        <button type="submit" class="btn btn-primary">Sauvegarder</button>
                    </form>
                </div>
                
                <div class="col-md-8">
                    <h2>Offres d'emploi</h2>
                    <input type="text" class="form-control mb-3" id="jobFilter" placeholder="Filtrer les offres...">
                    
                    <div class="list-group">
                        {% for job in jobs %}
                        <div class="list-group-item">
                            <h5 class="mb-1">{{ job.title }}</h5>
                            <p class="mb-1">{{ job.company }}</p>
                            <p class="mb-1">{{ job.location }}</p>
                            <small>Source: {{ job.source }} - Date: {{ job.date_added }}</small>
                            <br>
                            <a href="{{ job.link }}" target="_blank" class="btn btn-sm btn-primary mt-2">Voir l'offre</a>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(template_content)
    
    print("Template créé avec succès!")
    
    # 3. Redémarrer l'application
    print("Redémarrage de l'application...")
    try:
        # Tuer tout processus Python existant sur le port 5000
        os.system('taskkill /f /im python.exe')
    except:
        pass
    
    # 4. Démarrer l'application
    subprocess.Popen([sys.executable, 'app.py'])
    
    print("Application redémarrée! Vous pouvez maintenant accéder à:")
    print("1. http://127.0.0.1:5000 - Pour voir l'interface")
    print("2. http://127.0.0.1:5000/trigger-scraping - Pour déclencher le scraping")