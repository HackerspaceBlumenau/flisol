import argparse
import http.server
import mimetypes
import os
import shutil
import socketserver
from urllib.parse import urljoin, urlparse

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = "templates"
STATIC_DIR = "static"
OUTPUT_DIR = "output"


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/flisol/")
            self.end_headers()
            return

        page = self.path.lstrip("/").replace("flisol/", f"{OUTPUT_DIR}/")

        if os.path.isfile(page):
            self.send_file(page)
            return

        if os.path.isfile(page + ".html"):
            self.send_file(page + ".html")
            return

        if os.path.isfile(page + "index.html"):
            self.send_file(page + "index.html")
            return

        self.send_error(404, "File not found")

    def send_file(self, filepath):
        ctype = mimetypes.guess_type(filepath)[0] or "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.end_headers()

        with open(filepath, "rb") as f:
            self.wfile.write(f.read())


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

        site_url = config["url"]
        assert site_url is not None, f"Missing 'url' in '{path}'."

        editions = config.get("editions")
        assert editions is not None, f"Missing 'editions' in '{path}'."

        current_edition = config.get("current_edition")
        assert current_edition is not None, f"Missing 'current_edition' in '{path}'."

        for edition in editions:
            year = edition.get("year")
            assert year, f"Missing 'year' for one of the editions in '{path}'."

            pages = edition.get("pages")
            assert pages is not None, f"Missing 'pages' for {year} edition in '{path}'."

            if year == current_edition:
                # current year get root directory
                edition_full_url = site_url
                output_dir = OUTPUT_DIR
            else:
                # previous year get year directory
                edition_full_url = urljoin(site_url, str(year))
                output_dir = os.path.join(OUTPUT_DIR, str(year))

            if not edition_full_url.endswith("/"):
                # ensure / at the end
                edition_full_url = edition_full_url + "/"

            edition["output_dir"] = output_dir
            edition["full_url"] = edition_full_url
            edition["url"] = urlparse(edition_full_url).path

            for page in pages:
                slug = page.get("slug")
                assert slug is not None, f"Missing 'slug' for page in {year} edition in '{path}'."

                output_path = os.path.join(output_dir, slug) + ".html"

                page_full_url = urljoin(edition_full_url, slug)
                page_url = urlparse(page_full_url).path

                page["full_url"] = page_full_url
                page["url"] = page_url
                page["output_path"] = output_path

        return config


def ensure_path(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def copy_static():
    src = STATIC_DIR
    dst = os.path.join(OUTPUT_DIR, STATIC_DIR)

    if not os.path.exists(src):
        return

    os.makedirs(dst, exist_ok=True)

    print("Copying static files...")
    shutil.copytree(src, dst, dirs_exist_ok=True)


def render(config_file):
    config = load_config(config_file)

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # cleanup old files
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for edition in config["editions"]:
        edition_full_url = edition["full_url"]
        edition_year = edition["year"]

        print(f"Redering FLISoL {edition_year}...")

        for page in edition["pages"]:
            template_name = page["template"]
            output_path = page["output_path"]

            template = env.get_template(f"{template_name}.html")
            rendered = template.render(
                site=config,
                edition=edition,
                page=page,
                get_menu_url=lambda slug: urlparse(urljoin(edition_full_url, slug)).path,
            )

            ensure_path(output_path)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rendered)

            print(f"Rendered {template_name} -> {output_path}")

    copy_static()
    print("Done.")


def serve(host, port):
    with ReusableTCPServer((host, port), Handler) as httpd:
        print(f"Serving at http://{host}:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            httpd.shutdown()
            httpd.server_close()


def main():
    parser = argparse.ArgumentParser(description="FLISoL")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("-c", "--config", required=True, help="Path to the configuration file")
    server_parser = subparsers.add_parser("server")
    server_parser.add_argument("-H", "--host", default="127.0.0.1", help="Host to listen on (default: 127.0.0.1)")
    server_parser.add_argument("-p", "--port", type=int, default=5000, help="Port to listen on (default: 5000)")

    args = parser.parse_args()

    if args.command == "render":
        render(args.config)
    elif args.command == "server":
        serve(args.host, args.port)


if __name__ == "__main__":
    main()
