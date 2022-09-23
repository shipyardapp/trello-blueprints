import argparse
import sys
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
    args = parser.parse_args()
    return args


def get_list_id_from_name(api_key, token, board_name, list_name):
    """Gets the Trello List id given the Name of the List and the board it's from"""
    get_url = f"https://api.trello.com/1/members/me/boards"
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
                board_list = board['lists']

        # get list id from board lists
        l_id = [b_list['id'] for b_list in board_list if b_list['name'] == list_name]

        # return list id as a str
        return l_id[0]

    elif get_response.status_code == 401: # incorrect credentials
        print("You do not have the required permissions or wrong credentials")
        sys.exit(exit_codes.INVALID_CREDENTIALS)

    else: # Some other error
        print(
            f"Unknown HTTP Status: {response.status_code} occured during request.",
            f"response: {response.text}"
        )
        sys.exit(exit_codes.UNKNOWN_ERROR) 



def create_ticket(api_key, token, id_list, name, description, start_date=None, due_date=None):
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
    if start_date:
        query['start'] = start_date
    if due_date:
        query['due'] = due_date,

    response = requests.post(url,headers=headers, json=query)

    if response.status_code == 200:
        print(f"Card created successfully")
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
    

def main():
    args = get_args()
    api_key = args.api_key
    access_token = args.access_token
    board_name = args.board_name
    list_name = args.list_name
    # get list id
    list_id = get_list_id_from_name(api_key, access_token, 
                    board_name, list_name)

    card_data = create_ticket(
            api_key, 
            access_token, 
            list_id, 
            args.name, 
            args.description, 
            args.start_date, 
            args.due_date
    )
    card_id = card_data['id']
    
    # save card to responses
    card_data_filename = shipyard.files.combine_folder_and_file_name(
        artifact_subfolder_paths['responses'],
        f'create_ticket_{card_id}_response.json')
    shipyard.files.write_json_to_file(card_data, card_data_filename)


if __name__ == "__main__":
    main()