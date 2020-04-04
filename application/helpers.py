from flask import render_template


def render_404():
    return render_template('404.html'), 404
