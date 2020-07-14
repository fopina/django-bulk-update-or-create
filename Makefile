.PHONY: flake8 test coverage style style_check

style:
	black --target-version=py36 bulk_update_or_create tests setup.py
	flake8 bulk_update_or_create tests

style_check:
	black --target-version=py36 --check bulk_update_or_create tests setup.py

flake8:
	flake8 bulk_update_or_create tests

startmysql:
	@docker inspect django-bulk_update_or_create-mysql | grep -q '"Running": true' || \
		docker run --name django-bulk_update_or_create-mysql \
		           -e MYSQL_ROOT_PASSWORD=root \
		           --rm -p 8877:3306 -d \
				   --health-cmd "mysqladmin ping" \
				   --health-interval 10s \
				   --health-timeout 5s \
				   --health-retries=5 \
				   mysql:5  # TODO: wait for healthy

startpg:
	@docker inspect django-bulk_update_or_create-pg | grep -q '"Running": true' || \
		docker run --name django-bulk_update_or_create-pg \
		           -e POSTGRES_USER=postgres \
          		   -e POSTGRES_PASSWORD=postgres \
				   -e POSTGRES_DB=postgres \
		           --rm -p 8878:5432 -d \
				   --health-cmd pg_isready \
				   --health-interval 10s \
				   --health-timeout 5s \
				   --health-retries 5 \
				   postgres:10  # TODO: wait for healthy

test: startmysql
	DJANGO_SETTINGS_MODULE=settings_mysql \
		tests/manage.py test $${TEST_ARGS:-tests}

testpg: startpg
	DJANGO_SETTINGS_MODULE=settings_postgresql \
		tests/manage.py test $${TEST_ARGS:-tests}

testcmd: startpg startmysql
	# default - sqlite
	DJANGO_SETTINGS_MODULE=settings tests/manage.py migrate
	DJANGO_SETTINGS_MODULE=settings tests/manage.py bulk_it

	# mysql
	DJANGO_SETTINGS_MODULE=settings_mysql tests/manage.py migrate
	DJANGO_SETTINGS_MODULE=settings_mysql tests/manage.py bulk_it
	
	# postgres
	DJANGO_SETTINGS_MODULE=settings_postgresql tests/manage.py migrate
	DJANGO_SETTINGS_MODULE=settings_postgresql tests/manage.py bulk_it

coverage:
	PYTHONPATH="tests" \
		python -b -W always -m coverage run tests/manage.py test $${TEST_ARGS:-tests}
	coverage report
