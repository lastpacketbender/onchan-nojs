import threading, time, os
from data import count_image_removal_queue, select_image_removal_queue, clear_image_removal_queue
from config import config

class BackgroundFilePurge(threading.Thread):
    def run(self,*args,**kwargs):
        while True:
            if count_image_removal_queue() > 0:
                images = select_image_removal_queue()
                for image in images:
                    if os.path.isfile(image):
                        os.remove(image)
                        print("%s purged" % image)
                    else:
                        # If it fails, inform the user.
                        print("%s file not found for removal, skipping..." % image)
                clear_image_removal_queue()
            time.sleep(config['data']['purge_delay'])
