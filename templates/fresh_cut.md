## Fresh Cut
{% if announcements %}
{%- for announcement in announcements %}
- {{ announcement.content }} [Read announcement →]({{ announcement.url }})
{%- endfor %}
{%- else %}
*No announcements this week*
{%- endif %}

---