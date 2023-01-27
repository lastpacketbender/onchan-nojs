import os, random, hashlib, struct, imghdr, calendar
from datetime import datetime
from config import config

def image_dimensions(fname):
    '''Determine the image type of fhandle and return its size.
    from draco'''
    with open(fname, 'rb') as fhandle:
        head = fhandle.read(24)
        if len(head) != 24:
            return
        if imghdr.what(fname) == 'png':
            check = struct.unpack('>i', head[4:8])[0]
            if check != 0x0d0a1a0a:
                return
            width, height = struct.unpack('>ii', head[16:24])
        elif imghdr.what(fname) == 'gif':
            width, height = struct.unpack('<HH', head[6:10])
        elif imghdr.what(fname) == 'jpeg':
            try:
                fhandle.seek(0) # Read 0xff next
                size = 2
                ftype = 0
                while not 0xc0 <= ftype <= 0xcf:
                    fhandle.seek(size, 1)
                    byte = fhandle.read(1)
                    while ord(byte) == 0xff:
                        byte = fhandle.read(1)
                    ftype = ord(byte)
                    size = struct.unpack('>H', fhandle.read(2))[0] - 2
                # We are at a SOFn block
                fhandle.seek(1, 1)  # Skip `precision' byte.
                height, width = struct.unpack('>HH', fhandle.read(4))
            except Exception: #IGNORE:W0703
                return
        elif imghdr.what(fname) == 'bmp':
            # TODO
            pass
        else:
            return
        return width, height

def convert_unit(size_in_bytes):
    if not size_in_bytes:
        return None
    """ Convert the size from bytes to other units like KB, MB or GB"""
    meg = 1024*1024
    if size_in_bytes < meg:
        return '{} {}'.format(round(size_in_bytes/1024, 1), 'KB')
    elif size_in_bytes >= meg:
        return '{} {}'.format(round(size_in_bytes/meg, 1), 'MB')
    else:
        return '{} {}'.format(round(size_in_bytes, 1), 'B')

# TODO: Cleanup this nightmare. Some validations occur in service.py now
def save_image(data):
    if data and data.file:
        _, ext = os.path.splitext(data.filename)
        if ext.lower() not in ('.bmp', '.png', '.jpg', '.jpeg', '.gif', '.tiff', '.webm'):
            return False, None, None, None, "File extension not allowed."
        data.file.seek(0, os.SEEK_END)
        size = data.file.tell()
        if size > 10e6: # 10 MB limit
            return False, None, None, None, "File larger than 5 MB"
        data.file.seek(0, os.SEEK_SET)
        # TODO: Verify image headers, check for steganography
        raw = data.file.read() # This is dangerous for big files
        data.file.close()
        filename = data.filename
        save_path = f"{os.getcwd()}/{config['images']['dir']}"
        # TODO: Use sequence in table that wraps at 8 digits
        image_id = calendar.timegm(datetime.now().timetuple())
        saved_filename = f"{str(image_id)}{ext}"
        save_file = f"{save_path}/{saved_filename}"
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        with open(save_file, "wb") as file:
            if type(raw) == bytes: 
                file.write(raw)
            # Hm, will we support pgm?
            elif type(raw) == str: 
                file.write(raw.encode("utf-8"))
            m = hashlib.sha512()
            m.update(raw)
            print("Uploaded %s to %s (%d bytes)." % (filename, save_file, len(raw)))
        return True, image_id, saved_filename, size, m.hexdigest(), "Uploaded %s to %s (%d bytes)." % (filename, save_file, len(raw))