# Lateshell
A small custom shell for interacting with the box of the HackTheBox challenge [Late](https://app.hackthebox.com/machines/463)

The server takes an image, converts it into text and sends the text back as a text file.
Because it uses templating engine **Jinja2** on the text before it sends it backs, it is vulnerable to a SSTI (Server side templating injection).

Lateshell takes advantage of this, takes any shell command, generated a payload from it, and sends it to the server as an image.
Providing a shell-like experience.
