import logging
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont
from .main_window import MainWindow
from .paths import AppPaths
from .logging_setup import configure_logging, install_exception_hooks


def run(base_dir=None):
    paths = AppPaths.discover(base_dir)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("AgroClima Monitor")
    app.setFont(QFont("Segoe UI", 10))
    restore_hooks = lambda: None
    logger = logging.getLogger(__name__)
    try:
        configure_logging(paths)
        restore_hooks = install_exception_hooks()
        logger.info("Inicialização do AgroClima Monitor 2.0")
        app.setStyleSheet(paths.stylesheet.read_text(encoding="utf-8"))
        window = MainWindow(paths.root)
        window.show()
        if "--demo" in sys.argv:
            logger.info("Modo demonstração iniciado")
            window.start_demo()
        return app.exec()
    except Exception:
        logger.exception("Falha na inicialização ou execução")
        QMessageBox.critical(
            None,
            "AgroClima Monitor",
            "Não foi possível iniciar o aplicativo. Confira a pasta completa do projeto, "
            "as permissões de escrita e o arquivo logs/agroclima.log, quando disponível.",
        )
        return 1
    finally:
        logger.info("Aplicativo encerrado")
        restore_hooks()
