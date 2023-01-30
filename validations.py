import os
from data import select_board, select_thread

# VALIDATIONS

def validate_file(data):
    messages = []
    supported_files = ('.bmp', '.png', '.jpg', '.jpeg', '.gif', '.tiff', '.webm')
    if data.filename != "empty":
        _, ext = os.path.splitext(data.filename)
        if not ext:
            messages.append("image required")
        elif ext and ext.lower() not in supported_files:
            messages.append("not a supported filetype")
        else:
            # File is attached and non-zero in size
            data.file.seek(0, os.SEEK_END)
            size = data.file.tell()
            data.file.seek(0, os.SEEK_SET)
            if size <= 0:
                messages.append("empty file found")
            elif size >= 1024 ** 2 * 5:
                messages.append("file larger than 5 MB limit")
    else:
        messages.append("image required")
    return True if len(messages) == 0 else False, messages

def validate_options(options):
    messages = []
    options = options.split(" ")
    valid_options = True
    if len(options) == 1 and options[0] != '':
        for option in options:
            if option == "sage" or option == "nonokosage" or option == "nonoko":
                continue
            elif "##" in option:
                name, password = option.split("##")
                if len(name) > 0 and len(password) > 0:
                    continue
                else:
                    messages.append(f"invalid secure trip code '{option}'")
                    valid_options = False
            elif "#" in option:
                name, password = option.split("#")
                if len(name) > 0 and len(password) > 0:
                    continue
                else:
                    messages.append(f"invalid trip code '{option}'")
                    valid_options = False
            else:
                messages.append(f"invalid option '{option}' found")
                valid_options = False
    return valid_options, messages, options if len(messages) == 0 else None

def validate_comment(comment):
    messages = []
    if len(comment) > 2000:
        messages.append("comment is larger than 2000 character limit")
    return True if len(messages) == 0 else False, messages

def validate_new_thread(name, subject, options, comment, data):
    # TODO: length of name, subject, options
    valid_file, file_messages = validate_file(data)
    
    # if not name: Defaulted in database
    valid_comment, comment_messages = validate_comment(comment)

    valid_options, options_messages, options = validate_options(options)
    
    return valid_comment and valid_file and valid_options, ', '.join(file_messages + comment_messages + options_messages), options

def validate_new_reply(name, options, comment, data, path, thread):
    # TODO: length of name, subject, options
    if data.filename != 'empty':
        board = select_board(f"{path}", 1)
        content = select_thread(path, thread, limit=100)

        if content.num_image_replies < board.image_limit:
            valid_file, file_messages = validate_file(data)
        else:
            valid_file, file_messages = False, ["Image limit reached"]
    else:
        # Skip, images aren't required in replies
        valid_file, file_messages = True, []
    
    # if not name: Defaulted in database
    valid_comment, comment_messages = validate_comment(comment)
    valid_options, options_messages, options = validate_options(options)
    
    return valid_comment and valid_file and valid_options, ', '.join(file_messages + comment_messages + options_messages), options

