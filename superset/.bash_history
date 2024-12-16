superset fab reset-password --username admin
superset fab reset-password --username admin
superset db upgrade
export FLASK_APP=superset
superset fab create-admin
superset init
docker restart apache-superset
exit
pip install psycopg2-binary
exit
