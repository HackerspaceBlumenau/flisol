PROJECT = flisol
CURRENT_DIR = $(shell pwd)
PORT = 8081

container:
	@docker run \
		--name=$(PROJECT) \
		-p $(PORT):80 \
		-v $(CURRENT_DIR):/usr/local/apache2/htdocs/$(PROJECT) \
		-d httpd:2.4

delete_container:
	@docker rm -f $(PROJECT)

local: delete_container container
	@echo "Access http://localhost:$(PORT)/$(PROJECT)"
