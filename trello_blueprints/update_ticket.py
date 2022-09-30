import argparse
import sys
import requests
import re
from datetime import datetime
from ast import literal_eval
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
    parser.add_argument('--card-shortlink', dest="card_link", required=True)
    parser.add_argument('--name', dest='name', required=False)
    parser.add_argument('--description', dest='description', required=False)
    parser.add_argument('--board-name', dest='board_name', required=False)
    parser.add_argument('--list-name', dest='list_name', required=False)
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

    if get_response.status_code == 200:
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

    if get_response.status_code == 200:
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


def update_ticket(api_key, token, card_id, query_data):
    """ Triggers the Update API and adds a new card
    https://developer.atlassian.com/cloud/trello/rest/api-group-cards/#api-cards-id-put
    """
    
    url = f"https://api.trello.com/1/cards/{card_id}"

    headers = {
       "Accept": "application/json"
    }

    query = {
       'key': api_key,
       'token': token
    }
    # add additional query data
    query.update(query_data)
    response = requests.put(url, headers=headers, data=query)

    if response.status_code == 200:
        print(f"Card with id {card_id} updated successfully")
        return response.json()
        
    elif response.status_code == 401: # Permissions Error
        print("You do not have the required permissions")
        sys.exit(exit_codes.INVALID_CREDENTIALS)

    elif response.status_code == 400: # Bad Request
        print("Trello Update responded with Bad Request Error. ",
              f"Response message: {response.text}")
        sys.exit(exit_codes.BAD_REQUEST)

    else: # Some other error
        print("an Unknown Error has occured when attempting your update request:",
              f"{response.text}")
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


def get_card_data(api_key, token, card_shortlink):
    """ Get data related to the card."""

    card_url = f"https://api.trello.com/1/cards/{card_shortlink}/"
    
    headers = {
       "Accept": "application/json"
    }
    params = {
       'key': api_key,
       'token': token
    }
    response = requests.get(card_url,
                             headers=headers,
                             params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error:{response.status_code} Card ShortLink {card_shortlink} not found in Trello")
        sys.exit(exit_codes.BAD_REQUEST)
    

def main():
    args = get_args()
    access_token = args.access_token
    api_key = args.api_key
    card_shortlink = args.card_link
    source_file_name = args.source_file_name
    source_folder_name = args.source_folder_name
    source_file_name_match_type = args.source_file_name_match_type

    # get board_id and card_id from card data
    card_data = get_card_data(api_key, access_token, card_shortlink)
    board_id = card_data['idBoard']
    card_id = card_data['id']

    # create payload dict and add data to it
    query_data = {}
    if args.name:
        query_data['name'] = args.name
    if args.description:
        query_data['description'] = args.description
    if args.start_date:
        query_data['start'] = convert_date_to_trello(args.start_date)
    if args.due_date:
        query_data['due'] = convert_date_to_trello(args.due_date)  
    if args.due_complete:
        query_data['dueComplete'] = args.due_complete
    if args.members_list:
        member_ids = get_label_ids_from_name(api_key, access_token, 
                                          board_id, literal_eval(args.members_list))
        query_data['idMembers'] = member_ids
    if args.labels_list:
        label_ids = get_label_ids_from_name(api_key, access_token, 
                                          board_id, literal_eval(args.labels_list))
        query_data['idLabels'] = label_ids
    if args.url_source:
        query_data['urlSource'] = args.url_source
    if args.address:
        query_data['address'] = args.address
    if args.location_name:
        query_data['locationName'] = args.location_name
    if args.coordinates:
        query_data['coordinates'] = args.coordinates
    if args.board_name:
        query_data['idBoard'] = get_board_id_from_name(
                    api_key, access_token, args.board_name)
    if args.list_name:
        query_data['idList'] = get_list_id_from_name(api_key, access_token, 
                    query_data['idBoard'], args.list_name)
    
    updated_data = update_ticket(
            args.api_key, 
            args.access_token, 
            card_shortlink,
            query_data
    )
    # add attachment logic
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
        f'update_ticket_{card_id}_response.json')
    shipyard.files.write_json_to_file(updated_data, card_data_filename)


if __name__ == "__main__":
    main()