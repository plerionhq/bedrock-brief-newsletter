## Core Sample

{%- if featured_video %}
**{{ featured_video.title }}**

{{ featured_video.summary }} [Watch video →]({{ featured_video.url }})
{%- else %}
No videos this week
{%- endif %}

{% if other_videos %}
**More videos:**
{% for video in other_videos %}
- [{{ video.title }}]({{ video.url }})
{%- endfor %}
{%- endif %}

---