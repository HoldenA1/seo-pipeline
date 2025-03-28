# LLM Powered Business Article Generator

This project is intended to be an automated pipeline that generates articles using an LLM, then publishes them on a website. The goal is to automate the entire process so that it can generate and publish content entirely autonomously.

## Project Structure

### Folders

- services
  - author_service
  - scout_service
  - site_generator_service
- shared
- website

### Services

#### Scout

The scout service uses the Google Places API (New) to learn about new businesses and gather data on them. It stores the gathered data in a sqlite database that it shares with the other services.

#### Author

The author service takes business data that was scraped by the scout and prompts an LLM to write the article content. The results of this prompt are formatted and stored in a content management system (CMS). We are currently using Strapi CMS to manage content.

#### Site Generator

The site generator service queries the CMS and turns the content into pre-rendered html pages that can be served to users quickly.
