## The Quarry

{%- if featured_blog %}
**{{ featured_blog.title }}**

{{ featured_blog.summary }} [Read blog →]({{ featured_blog.url }})
{%- endif %}

{% if other_blogs %}
**More posts:**
{% for blog in other_blogs %}
- [{{ blog.title }}]({{ blog.url }}) 
{%- endfor %}
{% endif %}

---