import argparse
import cloudscraper
from bs4 import BeautifulSoup
import winsound
import time
import os
import gc
import requests
from datetime import datetime

url = "https://www.yoursite.tv/index.php"
scraper = cloudscraper.create_scraper()

def print_available_message(performer_name):
    timestamp = datetime.now().strftime("%H:%M - %d.%m.%Y")
    print(f"\033[92m\n{timestamp} :: {performer_name} is available!\033[0m")

def print_not_available_message(performer_name):
    timestamp = datetime.now().strftime("%H:%M - %d.%m.%Y")
    print(f"\033[91m\n{timestamp} :: {performer_name} not available! Waiting...\033[0m")

def print_network_error_message():
    print("Network error occurred. Retrying connection...")

def print_connection_restored_message():
    print("Connection restored successfully.")

def get_performers():
    response = scraper.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    performers = soup.find_all("div", {"class": "row row-cols-2 row-cols-lg-6 row-cols-md-4 row-cols-sm-2 m-0 p-0 performer-list"})
    performer_names = []
    
    for performer in performers:
        performer_links = performer.find_all("div", {"class": "d-flex h-100 w-100 start-0 bottom-0 z-index-1 grad-bg align-items-end"})
        for link_div in performer_links:
            link = link_div.find("strong")
            if link:
                performer_name = link.text.strip()
                performer_names.append(performer_name)
    
    return performer_names

def check_performer_availability(performer_name):
    connection_lost = False

    while True:  # Retry loop
        try:
            response = scraper.get(url)
            if connection_lost:
                print_connection_restored_message()
                is_available = perform_availability_check(performer_name)
                if is_available:
                    print_available_message(performer_name)
                else:
                    print_not_available_message(performer_name)
            break  # Exit the loop if the request succeeds
        except requests.exceptions.RequestException:
            if not connection_lost:
                print_network_error_message()
            connection_lost = True
            time.sleep(5)  # Wait before retrying

    soup = BeautifulSoup(response.content, "html.parser")
    performers = soup.find_all("div", {"class": "row row-cols-2 row-cols-lg-6 row-cols-md-4 row-cols-sm-2 m-0 p-0 performer-list"})

    for performer in performers:
        performer_links = performer.find_all("div", {"class": "d-flex h-100 w-100 start-0 bottom-0 z-index-1 grad-bg align-items-end"})
        for link_div in performer_links:
            link = link_div.find("strong")
            if link:
                performer_name_on_site = link.text.strip()
                if performer_name_on_site == performer_name:
                    return True

    return False

def perform_availability_check(performer_name):
    is_available = check_performer_availability(performer_name)
    return is_available

def main(search_values):
    print("SDTV Performer Tracker v5")
    print("=========================")

    os.system('cls' if os.name == 'nt' else 'clear')

    if not search_values:
        print("No performers provided. Listing available performers...\n")
        print("SDTV Performer Tracker v5")
        print("=========================")
        available_performers = get_performers()
        for performer in available_performers:
            print(performer)

        selected_performer = input("\nEnter the name of the performer you want to follow: ")
        os.system('cls' if os.name == 'nt' else 'clear')
        search_values = [selected_performer]

    was_found = {search_value: False for search_value in search_values}
    was_printed = {search_value: False for search_value in search_values}

    while True:
        for performer_name in search_values:
            is_available = check_performer_availability(performer_name)
            
            if is_available and not was_found[performer_name]:
                print_available_message(performer_name)
                winsound.Beep(900, 100)
                was_found[performer_name] = True
                was_printed[performer_name] = True
            
            elif is_available and was_found[performer_name]:
                winsound.Beep(900, 100)
            
            elif not is_available:
                if was_found[performer_name] or not was_printed[performer_name]:
                    print_not_available_message(performer_name)
                was_found[performer_name] = False
                was_printed[performer_name] = True

        time.sleep(5)
        gc.collect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SDTV Performer Tracker")
    parser.add_argument("performers", nargs="*", help="Performer names to follow")
    args = parser.parse_args()

    main(args.performers)

