from flask import Flask, g, session, request, redirect, flash, abort, url_for
from flask_mail import Mail
from shotglass2 import shotglass
from shotglass2.takeabeltof.database import Database
from shotglass2.takeabeltof.jinja_filters import register_jinja_filters
from shotglass2.tools.views import tools
from shotglass2.users.admin import Admin
from shotglass2.users.models import User
from inventory import inventory
from inventory.views import item

# Create app
# setting static_folder to None allows me to handle loading myself
app = Flask(__name__, instance_relative_config=True,
        static_folder=None)
app.config.from_pyfile('site_settings.py', silent=True)

@app.before_first_request
def start_logging():
    shotglass.start_logging(app)


@app.context_processor
def inject_site_config():
    # Add 'site_config' dict to template context
    return {'site_config':shotglass.get_site_config()}


# work around some web servers that mess up root path
from werkzeug.contrib.fixers import CGIRootFix
if app.config['CGI_ROOT_FIX_APPLY'] == True:
    fixPath = app.config.get("CGI_ROOT_FIX_PATH","/")
    app.wsgi_app = CGIRootFix(app.wsgi_app, app_root=fixPath)

register_jinja_filters(app)
inventory.register_jinja_filters(app)

mail = Mail(app)

def init_db(db=None):
    # to support old code
    initalize_all_tables(db)

def initalize_all_tables(db=None):
    """Place code here as needed to initialze all the tables for this site"""
    if not db:
        db = get_db()
        
    shotglass.initalize_user_tables(db)
    
    ### setup any other tables you need here....
    inventory.initalize_tables(db)
    
def get_db(filespec=None):
    """Return a connection to the database.
    If the db path does not exist, create it and initialize the db"""
    
    if not filespec:
        filespec = shotglass.get_site_config()['DATABASE_PATH']
        
    # This is probobly a good place to change the
    # filespec if you want to use a different database
    # for the current request.
    
        
    # test the path, if not found, create it
    initialize = shotglass.make_db_path(filespec)
        
    g.db = Database(filespec).connect()
    if initialize:
        initalize_all_tables(g.db)
            
    return g.db


@app.before_request
def _before():
    # Force all connections to be secure
    if app.config['REQUIRE_SSL'] and not request.is_secure :
        return redirect(request.url.replace("http://", "https://"))

    #ensure that nothing is served from the instance directory
    if 'instance' in request.url:
        abort(404)
        
    #import pdb;pdb.set_trace()
    
    shotglass.get_app_config(app)
    shotglass.set_template_dirs(app) #g.template_list is now a list of templates
    
    get_db()
    session.permanent = True
    
    # Is the user signed in?
    g.user = None
    if 'user' in session:
        g.user = session['user']
        
        
    g.admin = Admin(g.db) # This is where user access rules are stored
    g.admin.register(User,
            url_for('tools.view_log'),
            display_name='View Log',
            top_level = True,
            minimum_rank_required=500,
        )
    shotglass.user_setup() # g.admin now holds access rules Users, Prefs and Roles
    inventory.register_admin()
    
    # g.menu_items should be a list of dicts
    #  with keys of 'title' & 'url' used to construct
    #  the non-table based items in the main menu
    g.menu_items = [
        {'title':'Home','url':url_for('item.display')},
        {'title':'Inventory Items','url':url_for('item.display')},
        {'title':'Stock Report','url':url_for('item.stock_report')},
        ]
    
@app.teardown_request
def _teardown(exception):
    if 'db' in g:
        g.db.close()


@app.errorhandler(404)
def page_not_found(error):
    return shotglass.page_not_found(error)

@app.errorhandler(500)
def server_error(error):
    return shotglass.server_error(error)

#Register the static route
app.add_url_rule('/static/<path:filename>','static',shotglass.static)

#Register the home page
app.add_url_rule('/','display',item.display)

## Setup the routes for users
shotglass.register_users(app)

# setup www.routes...
shotglass.register_www(app)

# Setup inventory
inventory.register_blueprints(app)

app.register_blueprint(tools.mod)

if __name__ == '__main__':
    
    with app.app_context():
        # create the default database if needed
        initalize_all_tables()
        
    #app.run(host='localhost', port=8000)
    app.run()
    
    