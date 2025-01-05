document.addEventListener('DOMContentLoaded', function() {
    // Fonction pour charger les offres d'emploi
    function loadJobs() {
        fetch('/search')
            .then(response => response.json())
            .then(jobs => {
                const jobList = document.getElementById('jobList');
                jobList.innerHTML = '';
                
                jobs.forEach(job => {
                    const jobElement = document.createElement('div');
                    jobElement.className = 'list-group-item job-item';
                    jobElement.innerHTML = `
                        <h5 class="job-title">${job.title}</h5>
                        <p class="job-company">${job.company}</p>
                        <p class="job-location">${job.location}</p>
                        <p>${job.description}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">Publié le ${job.date}</small>
                            <a href="${job.url}" target="_blank" class="btn btn-primary btn-sm">Postuler</a>
                        </div>
                    `;
                    jobList.appendChild(jobElement);
                });
            })
            .catch(error => console.error('Erreur:', error));
    }

    // Gestion du formulaire de profil
    const profileForm = document.getElementById('profileForm');
    profileForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        
        fetch('/upload_portfolio', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            alert('Profil mis à jour avec succès!');
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert('Erreur lors de la mise à jour du profil');
        });
    });

    // Charger les offres au démarrage
    loadJobs();
    
    // Rafraîchir les offres toutes les 5 minutes
    setInterval(loadJobs, 300000);
});
