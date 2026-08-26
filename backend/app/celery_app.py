from celery import Celery, Task

from . import create_app


def celery_init_app(flask_app):
    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery = Celery(flask_app.name, task_cls=FlaskTask)
    celery.config_from_object(flask_app.config["CELERY"])
    celery.set_default()
    flask_app.extensions["celery"] = celery
    return celery


flask_app = create_app()
celery_app = celery_init_app(flask_app)

# Import after the default Celery application has been configured.
from . import tasks  # noqa: E402, F401

