"""
About Module — Flask Blueprint
Project information, developer credits, and module overview.
"""

from flask import Blueprint, render_template

about_bp = Blueprint('about', __name__)


@about_bp.route('/about')
def index():
    return render_template('about/index.html')
