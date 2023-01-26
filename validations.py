import os

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

def validate_comment(comment):
    messages = []
    if not comment:
        messages.append("comment is a required field")
    else:
        if len(comment) > 2000:
            messages.append("comment is larger than 2000 character limit")
    return True if len(messages) == 0 else False, messages

def validate_new_thread(name, subject, options, comment, data):
    # TODO: length of name, subject, options
    valid_file, file_messages = validate_file(data)
    
    # if not name: Defaulted in database
    valid_comment, comment_messages = validate_comment(comment)
    
    return valid_comment and valid_file, ', '.join(file_messages + comment_messages)

def validate_new_reply(name, options, comment, data):
    # TODO: length of name, subject, options
    if data.filename != 'empty':
        valid_file, file_messages = validate_file(data)
    else:
        # Skip, images aren't required in replies
        valid_file, file_messages = True, []
    
    # if not name: Defaulted in database
    valid_comment, comment_messages = validate_comment(comment)
    
    return valid_comment and valid_file, ', '.join(file_messages + comment_messages)

