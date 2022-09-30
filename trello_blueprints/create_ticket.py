import argparse
import sys
import re
from ast import literal_eval
from datetime import datetime
import requests
import shipyard_utils as shipyard
try:
    import exit_codes
except BaseException:
    from . import exit_codes


# create Artifacts folder paths
base_folder_name = shipyard.logs.determine_base_artifact_folder('trello')
artifact_subfolder_paths = shipyard.logs.determine_artifact_subfolders(
    base_folder_name)
shipyard.logs.create_artifacts_folders(artifact_subfolder_paths)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-key', dest='api_key', required=True)
    parser.add_argument('--access-token', dest='access_token', required=True)
    parser.add_argument('--name', dest='name', required=True)
    parser.add_argument('--description', dest='description', required=True)
    parser.add_argument('--board-name', dest='board_name', required=True)
    parser.add_argument('--list-name', dest='list_name', required=True)
    parser.add_argument('--start-date', dest='start_date', required=False)
    parser.add_argument('--due-date', dest='due_date', required=False)
    parser.add_argument('--due-complete', dest='due_complete', required=False)
    parser.add_argument('--members', dest='members_list', required=False)
    parser.add_argument('--labels', dest='labels_list', required=False)    
    parser.add_argument('--url-source', dest='url_source', required=False)
    parser.add_argument('--address', dest='address', required=False)
    parser.add_argument('--location-name', dest='location_name', required=False)
    parser.add_argument('--coordinates', dest='coordinates', required=False)
    parser.add_argument(
        '--source-file-name',
        dest='source_file_name',
        required=False)
    parser.add_argument(
        '--source-folder-name',
        dest='source_folder_name',
        default='',
        required=False)
    parser.add_argument('--source-file-name-match-type',
                        dest='source_file_name_match_type',
                        choices={'exact_match', 'regex_match'},
                        default='exact_match',
                        required=False)
    args = parser.parse_args()
    return args


def get_board_id_from_name(api_key, token, board_name):
    """Gets the Trello board id given the board_name"""
    get_url = "https://api.trello.com/1/members/me/boards"
    params = {
        'key': api_key,
        'token': token,
        'lists': 'all' # get all the lists data in response
    }
    get_response = requests.get(get_url, params=params)

    if get_response.status_code == requests.codes.ok:
        # get the board data from json response
        # [board for board in data if board['name'] == "Stuff"]
        trello_data = get_response.json()
        for board in trello_data:
            if board['name'] == board_name:
                return board['id']


def get_label_ids_from_name(api_key, token, board_id, labels):
    """Gets the Trello Label id given a list of Label names and board"""
    get_url = f"https://api.trello.com/1/boards/{board_id}/labels"
    params = {
        'key': api_key,
        'token': token,
    }
    get_response = requests.get(get_url, params=params)
    if get_response.status_code == 200:
        labels_data = get_response.json()
        # find and return the label
        label_ids = [
            label['id'] for label in labels_data if label['name'] in labels
        ]
        return label_ids
        

def get_member_ids_from_name(api_key, token, board_id, members):
    """Gets the Trello Member id given a list of members names and board"""
    get_url = f"https://api.trello.com/1/boards/{board_id}/memberships"
    params = {
        'key': api_key,
        'token': token,
    }
    get_response = requests.get(get_url, params=params)
    if get_response.status_code == 200:
        member_data = get_response.json()
        # find and return the label
        member_ids = [
            member['id'] for member in member_data if member['name'] in members
        ]
        return member_ids


def get_list_id_from_name(api_key, token, board_id, list_name):
    """Gets the Trello List id given the Name of the List and the board it's from"""
    get_url = f"https://api.trello.com/1/boards/{board_id}/lists"
    params = {
        'key': api_key,
        'token': token,
    }
    get_response = requests.get(get_url, params=params)

    if get_response.status_code == requests.codes.ok:
        # get the list data from json response
        lists_data = get_response.json()
        # get list id from board lists
        list_id = [
            b_list['id'] for b_list in lists_data if b_list['name'] == list_name
        ]
        if list_id:
            # return list id as a str
            return list_id[0]
        else:
            print(f"Error: No list with name {list_name} found")
            sys.exit(exit_codes.BAD_REQUEST)

    elif get_response.status_code == 401: # incorrect credentials
        print("You do not have the required permissions or wrong credentials")
        sys.exit(exit_codes.INVALID_CREDENTIALS)

    else: # Some other error
        print(
            f"Unknown HTTP Status: {get_response.status_code} occured during GET LIST ID.",
            f"response: {get_response.text}"
        )
        sys.exit(exit_codes.UNKNOWN_ERROR) 



def create_ticket(api_key, token, id_list, name, description, payload):
    """ Triggers the Create Card API and adds a new card
    https://developer.atlassian.com/cloud/trello/rest/api-group-cards/#api-cards-post
    """
    
    url = "https://api.trello.com/1/cards"

    headers = {
       "Accept": "application/json"
    }

    query = {
       'idList': id_list,
       'key': api_key,
       'token': token,
       'name': name,
       'desc': description
    }
    # add additional fields to the query
    query.update(payload)
    response = requests.post(url,headers=headers, json=query)

    if response.status_code == 200:
        print("Card created successfully")
        return response.json()
        
    elif response.status_code == 401: # Credentials Error
        print("You do not have the required permissions")
        sys.exit(exit_codes.INVALID_CREDENTIALS)

    elif response.status_code == 400: # Bad Request
        print("Trello responded with Bad Request Error. ",
              f"Response message: {response.text}")
        sys.exit(exit_codes.BAD_REQUEST)

    else: # Some other error
        print(
            f"Unknown HTTP Status: {response.status_code} occured during request.",
            f"response: {response.text}"
        )
        sys.exit(exit_codes.UNKNOWN_ERROR)
    

def attach_file_to_card(api_key, token, card_id, file_path):
    """ Attaches files to a Trello card."""

    attachment_endpoint = f"https://api.trello.com/1/cards/{card_id}/attachments"
    
    headers = {
       "Accept": "application/json"
    }
    params = {
       'key': api_key,
       'token': token
    }
    file_payload = {
        "file": (file_path, open(file_path, "rb"), "application-type")
    }
    response = requests.post(attachment_endpoint,
                             headers=headers,
                             params=params,
                             files=file_payload)

    if response.status_code == 200:
        print(f'{file_path} was successfully attached to {card_id}')
    return response


def convert_date_to_trello(shipyard_date):
    """Converts date from shipyard input MM/DD/YYYY to 
    ISO 8086 date plus Zulu (Z).
    """ 
    str_as_date = datetime.strptime(shipyard_date, '%m/%d/%Y')
    converted_date = str_as_date.isoformat() + "Z"
    return converted_date


def main():
    args = get_args()
    api_key = args.api_key
    access_token = args.access_token
    board_name = args.board_name
    list_name = args.list_name
    source_file_name = args.source_file_name
    source_folder_name = args.source_folder_name
    source_file_name_match_type = args.source_file_name_match_type

    # get board_id for use in the rest of the functions
    board_id = get_board_id_from_name(api_key, access_token, board_name)
    # get list id
    list_id = get_list_id_from_name(api_key, access_token, 
                    board_id, list_name)

    # create payload dict and add data to it
    payload = {}
    if args.start_date:
        payload['start'] = convert_date_to_trello(args.start_date)
    if args.due_date:
        payload['due'] = convert_date_to_trello(args.due_date)  
    if args.due_complete:
        payload['dueComplete'] = args.due_complete
    if args.members_list:
        member_ids = get_label_ids_from_name(api_key, access_token, 
                                          board_id, literal_eval(args.members_list))
        payload['idMembers'] = member_ids
    if args.labels_list:
        # get labels and members
        label_ids = get_label_ids_from_name(api_key, access_token, 
                                          board_id, literal_eval(args.labels_list))
        payload['idLabels'] = label_ids
    if args.url_source:
        payload['urlSource'] = args.url_source
    if args.address:
        payload['address'] = args.address
    if args.location_name:
        payload['locationName'] = args.location_name
    if args.coordinates:
        payload['coordinates'] = args.coordinates

    # create card
    card_data = create_ticket(
            api_key, 
            access_token, 
            list_id, 
            args.name, 
            args.description,
            payload=payload
    )
    card_id = card_data['id']
    
    # add attachments
    if args.source_file_name:
        if source_file_name_match_type == 'regex_match':
            all_local_files = shipyard.files.find_all_local_file_names(
                source_folder_name)
            matching_file_names = shipyard.files.find_all_file_matches(
                all_local_files, re.compile(source_file_name))
            for index, file_name in enumerate(matching_file_names):
                attach_file_to_card(api_key, 
                                    access_token, 
                                    card_id,
                                    file_name)
        else:
            source_file_path = shipyard.files.combine_folder_and_file_name(
                source_folder_name, source_file_name)
            attach_file_to_card(api_key, 
                                access_token, 
                                card_id,
                                source_file_path)
    
    # save card to responses
    card_data_filename = shipyard.files.combine_folder_and_file_name(
        artifact_subfolder_paths['responses'],
        f'create_ticket_{card_id}_response.json')
    shipyard.files.write_json_to_file(card_data, card_data_filename)


if __name__ == "__main__":
    main()