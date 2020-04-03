from werkzeug.utils import redirect


def render_404():
    return redirect('404.html'), 404
