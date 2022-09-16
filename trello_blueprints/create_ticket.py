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
    parser.add_argument('--name', dest='name', required=False)
    parser.add_argument('--description', dest='description', required=False)
    parser.add_argument('--id-list', dest='id_list', required=False)
    parser.add_argument('--id-members', dest='id_members', required=False)
    parser.add_argument('--start-date', dest='start_date', required=False)
    parser.add_argument('--due-date', dest='due_date', required=False)
    args = parser.parse_args()
    return args



def create_ticket(api_key, token, id_list, id_members, name, description, start_date, due_date):
    """ Triggers the Create Card API and adds a new card
    https://developer.atlassian.com/cloud/trello/rest/api-group-cards/#api-cards-post
    """
    
    url = "https://api.trello.com/1/cards"

    headers = {
       "Accept": "application/json"
    }

    query = {
       'idList': id_list,
       'idMembers': id_members,
       'key': api_key,
       'token': token,
       'due': due_date,
       'start': start_date,
       'name': name,
       'desc': description
    }

    response = requests.post(url,headers=headers, data=query)

    if response.status_code == requests.codes.ok:
        card_data =  response.json()
        print(f"Card created successfully")
        return response.json()
        
    elif response.status_code == 401: # Permissions Error
        print("You do not have the required permissions")
        sys.exit(exit_codes.INVALID_CREDENTIALS)

    elif response.status_code == 400: # Bad Request
        print("Trello responded with Bad Request Error. ",
              f"Response message: {response.text}")
        sys.exit(exit_codes.BAD_REQUEST)

    else: # Some other error
        print("an Unknown Error has occured when attempting your request:",
              f"{response.text}")
        sys.exit(exit_codes.UNKNOWN_ERROR)
    

def main():
    args = get_args()
    card_data = create_ticket(
            args.api_key, 
            args.access_token, 
            args.id_list, 
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