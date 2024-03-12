"""
Backupper Script
This script is for folks collecting lots of data automatically that needs to get backed up at certain intervals

for instance saving a bunch of files to a folder, but then automatically copying them to larger external devices

This script first defines paths for the desktop, photos folder, and backup folder name. Then, it defines functions to:

    Get the storage information (total and available space) of a path.
    Find the sizes of all external devices in terms of total storage capacity (not available because this will change)
    Rank them in order  of their total storage capacity
    Check if the first option has space available to copy the new files
      if not, choose the next option in terms of total storage
    Copy all the files from the internal storage to the external storage
    Move the files from the directory of "fresh" files to the internal "backedup" folder
    if the internal storage gets too small, delete the internal "backedup" folder

Finally, the script checks if the photos folder exists and then finds the largest external storage. It compares the total space and available space on both the desktop and the external storage to determine if the external storage has enough space for the backup. If so, it creates a backup folder on the external storage and copies the photos. Otherwise, it informs the user about insufficient space.

Note:

    This script assumes the user running the script has read and write permissions to the desktop and any external storage devices.
    You might need to adjust the user name in desktop_path depending on your Raspberry Pi setup.


"""

import os
import subprocess
import shutil
from pathlib import Path

# Define paths
desktop_path = Path(
    "/home/pi/Desktop/Mothbox"
)  # Assuming user is "pi" on your Raspberry Pi
photos_folder = desktop_path / "photos"
backedup_photos_folder = desktop_path / "photos_backedup"

backup_folder_name = "photos_backup"
internal_storage_minimum = 1


def get_storage_info(path):
    """
    Gets the total and available storage space of a path.

    Args:
        path: The path to the storage device.

    Returns:
        A tuple containing the total and available storage in bytes.
    """

    try:
        stat = os.statvfs(path)
        return stat.f_blocks * stat.f_bsize, stat.f_bavail * stat.f_bsize
    except OSError:
        return 0, 0  # Handle non-existent or inaccessible storages


def find_largest_external_storage():
    """
    Finds the largest external storage device connected to the Raspberry Pi.

    Returns:
        The path to the largest storage device or None if none is found.
    """
    largest_storage = None
    largest_size = 0

    for mount_point in os.listdir("/media/pi"):
        path = Path(f"/media/pi/{mount_point}")
        if path.is_dir():
            total_size, available_size = get_storage_info(path)
            print(path)
            print(available_size)
            if available_size > largest_size:
                largest_storage = path
                largest_size = available_size
            """
      if total_size > largest_size:
        largest_storage = path
        largest_size = total_size
      """
    print("Largest Storage: " + str(largest_storage))
    print(largest_size)
    return largest_storage


def rsync_photos_to_backup(source_dir, dest_dir):
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    # Build the rsync command with options for recursive copy, delete on source, and verbose output
    # rsync_cmd = ["rsync", "-avz", "--delete", source_dir, dest_dir] # copies the whole folder, not just files inside
    
    #rsync_cmd = ["rsync", "-av", str(source_dir) + "/", dest_dir]
    #if you don't want as many slow print commands, turn off verbose mode
    rsync_cmd = ["rsync", "-az", str(source_dir) + "/", dest_dir]

    # Call rsync using subprocess
    try:
        process = subprocess.run(rsync_cmd, check=True)
    except subprocess.CalledProcessError as err:
        raise RuntimeError(f"Oh no! Mothbox couldn't backup your files!") from err


def rsync_copy_and_delete_files(source_dir, dest_dir):
    """
    This function uses rsync to copy files from source_dir to dest_dir and then deletes the originals from source_dir if successful.

    Args:
      source_dir: The source directory containing the files to copy.
      dest_dir: The destination directory to copy the files to.

    Raises:
      subprocess.CalledProcessError: If the rsync command fails.
    """
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    # Build the rsync command with options for recursive copy, delete on source, and verbose output
    # rsync_cmd = ["rsync", "-avz", "--delete", source_dir, dest_dir] # copies the whole folder, not just files inside
    
    #rsync_cmd = ["rsync", "-av", str(source_dir) + "/", dest_dir] #verbose
    rsync_cmd = ["rsync", "-az", str(source_dir) + "/", dest_dir]

    
    # Call rsync using subprocess
    process = subprocess.run(rsync_cmd, check=True)

    # If successful, iterate through copied files and delete them individually
    if process.returncode == 0:
        for root, _, files in os.walk(source_dir):
            for filename in files:
                source_file = os.path.join(root, filename)
                dest_file = os.path.join(dest_dir, filename)
                # Check if the file was successfully copied (exists in destination)
                if os.path.isfile(dest_file):
                    try:
                        os.remove(source_file)
                        #print(f"Deleted: {source_file}")
                    except OSError as e:
                        print(f"Error deleting {source_file}: {e}")

    return process.returncode


# older way of just copying items in the folder
def copy_photos_to_backup(source_folder, target_folder):
    """
    Copies all files from the source folder to the target folder.

    Args:
        source_folder: The path to the source folder.
        target_folder: The path to the target folder.
    """
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    for filename in os.listdir(source_folder):
        source_path = os.path.join(source_folder, filename)
        target_path = os.path.join(target_folder, filename)
        shutil.copy2(source_path, target_path)  # Preserves file metadata


def delete_original_photos(source_folder):
    """
    Deletes all files from the source folder.

    Args:
        source_folder: The path to the source folder.
    """
    for filename in os.listdir(source_folder):
        file_path = os.path.join(source_folder, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except OSError as e:
            print(f"Error deleting file {file_path}: {e}")


if __name__ == "__main__":
    # Check if "photos" folder exists
    if not os.path.exists(photos_folder):
        print("Photos folder not found, exiting.")
        exit(1)

    # Find largest external storage
    # largest_storage = find_largest_external_storage()

    # Get total and available space on desktop and external storage
    desktop_total, desktop_available = get_storage_info(desktop_path)
    # external_total,external_available = get_storage_info(largest_storage)
    print("Desktop Total    Storage: \t" + str(desktop_total))
    print("Desktop Available Storage: \t" + str(desktop_available))

    """
  Finds storage capacity of all external drives and ranks them by size.
  """
    disks = {}  # Dictionary to store disk name and capacity

    # Check potential mount points for external drives (adjust based on your system)
    for mount_point in os.listdir("/media/pi"):
        path = Path(f"/media/pi/{mount_point}")
        if path.is_dir():
            total_size, available_size = get_storage_info(path)
            disks[path] = total_size, available_size

    # Sort disks by capacity (descending)
    # Check if any disks were found before sorting and printing
    print("~~~sorting disks~~~~~~")
    if disks:
        sorted_disks = sorted(disks.items(), key=lambda item: item[1][0], reverse=True)
        print("External Drives (Ranked by Total Size - Descending):")
        for disk_name, capacity in sorted_disks:
            print(
                f"{disk_name}: total size {capacity[0]} GB - available size {capacity[1]} GB"
            )
    else:
        print("No external drives found.")
        print(
            "stuff never worked out with this backup, your files are not properly backedup"
        )

        exit(1)

    print("~~~sorted~~~~~~")

    thingsworkedok = False
    # this is the loop where we make stuff happen
    # iterate through the disks, starting with the largest
    # see if it has enough available space, if not, choose the next largest
    for disk_name, capacity in sorted_disks:
        total_available, external_available = capacity
        # Check if external storage has more available space than desktop
        if external_available > sum(
            os.path.getsize(f) for f in photos_folder.iterdir() if f.is_file()
        ):

            # Create backup folder on external storage
            external_backup_folder = disk_name / backup_folder_name

            try:
                rsync_photos_to_backup(photos_folder, external_backup_folder)
                # Proceed to the next step if successful
                print(
                    f"Photos successfully copied to backup folder: {external_backup_folder}"
                )

                # since we were successful, move backed up images here!
                rsync_copy_and_delete_files(photos_folder, backedup_photos_folder)
                print(
                    f"Photos successfully copied to backed_up folder and deleted from fresh folder: {backedup_photos_folder}"
                )
                thingsworkedok = True

                # After we backed up, we can check on our internal storage and see if we need to clean up
                # Check if internal storage has less than X GB left
                x = internal_storage_minimum
                if desktop_available < x * 1024**3:  # x GB in bytes
                    delete_original_photos(backedup_photos_folder)
                    print(
                        "Original photos deleted after being backed up due to low internal storage."
                    )
                else:
                    print(
                        "More than "
                        + str(x)
                        + "GB remain so original files are also kept in internal storage after backing up to external storage"
                    )
                print("we have finished backing up! yay!")
                break
            except subprocess.CalledProcessError as err:
                print(
                    "Error during backup, moving to next available storage if there is one!:",
                    err,
                )
                thingsworkedok = False
        else:
            print(
                "This External storage doesn't have enough space for backup.\n Trying next available storage if there is one "
            )

    if thingsworkedok == False:
        print(
            "stuff never worked out with this backup, your files are not properly backedup"
        )
    else:
        print("BACKUP COMPLETE")
