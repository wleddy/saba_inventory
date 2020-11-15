## Welcome to the {{ config.SITE_NAME }}

{% if g.user %}
### Hello {{g.user}}!
You may want to view the [inventory list]({{ url_for('item.display')}})
{% else %}
In order to do anything fun, you'll need to [log in]({{ url_for('login.login')}})
{% endif %}