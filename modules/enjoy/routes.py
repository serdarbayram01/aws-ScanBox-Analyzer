"""
Enjoy Module — Flask Blueprint
Mini games for a fun break between operations.
"""

from flask import Blueprint, render_template

enjoy_bp = Blueprint('enjoy', __name__)


@enjoy_bp.route('/enjoy')
def index():
    """Render the Enjoy arcade page."""
    return render_template('enjoy/index.html')
