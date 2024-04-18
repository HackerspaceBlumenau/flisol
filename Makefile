PROJECT = flisol

setup:
	@gem install bundler
	@bundler init
	@bundler add jekyll

local: 
	@bundle exec jekyll serve -b /$(PROJECT)
