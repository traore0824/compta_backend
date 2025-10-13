#!/bin/bash
set -e

echo "🚀 Début du déploiement Connect Pro..."

# Variables de configuration
PROJECT_DIR="/root/connect_pro"
VENV_PATH="$PROJECT_DIR/.venv"

# 0. Navigation et activation
echo "📂 Navigation vers le répertoire du projet..."
cd "$PROJECT_DIR"

echo "🗄️ Activation du virtual env..."
source "$VENV_PATH/bin/activate"

# 1. Récupération du code
echo "📥 Git pull..."
git pull origin
#!/bin/bash
set -e  # Arrêter en cas d'erreur

# 2. Migrations
echo "🗄️ Création des migrations..."
python manage.py makemigrations

echo "🗄️ Application des migrations..."
python manage.py migrate

# 3. Arrêt des services
# echo "⏹️ Arrêt de Celery Beat..."
# sudo systemctl stop celerybeat-connectpro.service 2>/dev/null || true

echo "⏹️ Arrêt des workers Celery (via Supervisor)..."
sudo supervisorctl stop celery_connect

# Attendre que les workers s'arrêtent complètement
sleep 3

# Vérifier qu'ils sont bien arrêtés
REMAINING=$(pgrep -c -f "connect_pro.*worker" 2>/dev/null || echo 0)
if [ "$REMAINING" -gt 0 ]; then
    echo "   ⚠️ $REMAINING workers encore actifs, arrêt forcé..."
    pkill -9 -f "connect_pro.*worker" || true
    sleep 2
fi

# 4. Redémarrage des services
echo ""
echo "🔄 Redémarrage Gunicorn..."
sudo systemctl restart gunicorn_connect.service

echo "🔄 Redémarrage Daphne..."
sudo supervisorctl restart daphne_connect

echo "🔄 Redémarrage Celery Beat..."
sudo systemctl start celerybeat-connectpro.service

echo "🔄 Démarrage des workers Celery..."
sleep 2  # Attendre que Beat démarre complètement

# Démarrer les workers avec noms uniques
for i in $(seq 1 $CELERY_WORKERS); do
    echo "   Starting worker$i..."
    celery -A connect_pro worker --loglevel=info -n "worker$i@%h" --detach --pidfile="/tmp/celery_worker$i.pid"
done

# 7. Vérifications post-déploiement
echo "✅ Vérification des services..."

echo "--- Gunicorn Status ---"
sudo systemctl status gunicorn_connect.service --no-pager -l

echo "--- Celery Beat Status ---"
sudo systemctl status celerybeat-connectpro.service --no-pager -l

echo "--- Supervisor Status ---"
sudo supervisorctl status

echo "--- Workers Celery ---"
sleep 3  # Attendre que les workers démarrent
celery -A connect_pro inspect ping || echo "⚠️ Certains workers ne répondent pas encore"

echo "--- Vérification des tâches programmées ---"
celery -A connect_pro inspect scheduled | head -10

# 8. Nettoyage optionnel
echo "🧹 Nettoyage des fichiers temporaires..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + || true

# 9. Test de santé rapide
echo "🏥 Test de santé du système..."
python manage.py check --deploy || echo "⚠️ Certaines vérifications ont échoué"

echo ""
echo "🎉 Déploiement terminé avec succès !"
echo ""
echo "📊 Statut final des services :"
echo "   - Gunicorn: $(sudo systemctl is-active gunicorn.service)"
echo "   - Daphne: $(sudo supervisorctl status daphne_connect | awk '{print $2}')"
echo "   - Celery Beat: $(sudo systemctl is-active celerybeat-connectpro.service)"
echo "   - Workers: $(pgrep -c -f 'connect_pro worker' || echo 0) actifs"

echo ""
echo "📋 Commandes utiles post-déploiement :"
echo "   - Logs Celery Beat: sudo journalctl -u celerybeat-connectpro.service -f"
echo "   - Logs Gunicorn: sudo journalctl -u gunicorn.service -f"
echo "   - Logs Daphne: tail -f /var/log/daphne.log"
echo "   - Logs transactions: tail -f logs/transactions.log"
echo "   - Workers status: celery -A connect_pro inspect active"
echo "   - Restart workers: sudo supervisorctl restart celery_connect"
echo "   - Stop workers: sudo supervisorctl stop celery_connect"
echo "   - Supervisor status: sudo supervisorctl status"
echo ""

# Optionnel : Afficher les logs
read -p "Voulez-vous afficher les logs en temps réel ? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📜 Affichage des logs transactions (Ctrl+C pour quitter)..."
    tail -f logs/transactions.log
fi