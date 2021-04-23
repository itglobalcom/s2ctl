# Serverspace CLI

`s2ctl` is Serverspace on the command line. It brings ability to control your infrastructure in terminal as you already used to do it via web.

## Installation

`s2ctl` is available for Linux and Windows as single binary. Just download it from [Github](https://github.com/itglobalcom/s2ctl/releases) and extract.

### To install on Linux

1. Download file from Github:

```
wget https://github.com/itglobalcom/s2ctl/releases/download/vX.X.X/s2ctl-vX.X.X-linux.tar.gz
```
Here X.X.X is the number of latest release

2. Extract the downloaded archive:

```
tar -xzf s2ctl-vX.X.X-linux.tar.gz
```
You may also add the folder where you've put `s2ctl` binary to the PATH environment variable to access it from any place of your system. To see what's in your `$PATH` right now, type this into a terminal:

```
echo $PATH
```
To add a new directory to the list use the command:

```
export PATH=$PATH:"<download directory>"
```
The variable `$PATH` is set by your shell every time it launches, but you can set it so that it always includes your new path with every new shell you open. The exact way to do this depends on which shell you're running.

For example for Bash you need to add a line at the top about the appropriate file to be read when the shell starts:

```
echo 'export PATH=$PATH:"<download directory>"' >> .bashrc
```
To apply changes to current session type:

```
source ~/.bashrc
```

### To install on Windows

1. Download file **s2ctl-vX.X.X-windows.zip** from [Github](https://github.com/itglobalcom/s2ctl/releases) and extract it

2. Run the command line:

- Press `Win+R` or Start → text `run` → OK

- Enter the command `cmd` → OK

3. By default, the command line shows the directory of the current user. Navigate to the directory with the extracted file:

```
cd <extracted file directory>
```

4. After navigating to the required directory, run the command:

```
s2ctl
```

Set the PATH on Windows 10:

- In Search, search for and then select: System (Control Panel)

- Click the **Advanced system settings** link

- Click **Environment Variables**. In the section **System Variables** find the PATH environment variable and select it. Click **Edit**. If the PATH environment variable does not exist, click **New**

- In the **Edit System Variable** (or **New System Variable**) window, specify the value of the PATH environment variable. Click **OK**. Close all remaining windows by clicking **OK**.


## Before start

CLI uses the same mechanism as the Serverspace API therefore you should obtain API Key from settings of your project out of the control panel first. Then create a new context with this key and a name of you choice:

```
>s2ctl context create --name MyServers --key 04d1f...4ea4
```

Now you are ready to control your infrastructure:

```
>s2ctl project show
id: 1
balance: 1462.78
currency: EUR
state: Active
created: '1970-01-01T0:00:00.0000000Z'
```

## Usage

Serverspace CLI based on 2 common concepts: commands, that denote what to do, and arguments, that provide some data to commands.
Some commands are single-level such as `images` and `locations`. Some — are double-level, such as `server`, `network` and so on. This means that command is composed of two parts. The first part denotes an object and the second part denotes an action. Argument indicating an object id is passed without name. Other arguments are named. E.g. getting a server:
```
>s2ctl server get l1s12345
id: l1s12345
name: server-name
state: Active
created: '1970-01-01T0:00:00.0000000Z'
is_power_on: true
...
```

Or getting a volume of that server:
```
>s2ctl server get-volume l1s12345 --volume-id 20210
id: 20210
name: boot
server_id: l1s12345
size_mb: 25600
created: '1970-01-01T0:00:00.0000000Z'
```

At any time you can type `--help` to get list of commands:
```
>s2ctl --help
Usage: s2ctl [OPTIONS] COMMAND [ARGS]...

Options:
  -c, --config PATH  [default: C:\Users\ignat.tolchanov\AppData\Roaming\server
                     space.s2ctl\config.yaml]

  -k, --apikey TEXT
  --help             Show this message and exit.

Commands:
  context    Contexts are used for accessing concrete projects.
  images     List of OS images which you can use for your server.
  locations  List of places where our data centers are located.
  network    Manage isolated networks without Internet access.
  project    Various actions related to projects — containers of anyother...
  server     Manage virtual servers inside your project.
  ssh-key    SSH keys management.
  task       Many actions are long-running (e.g.
```

Or get list of second-level commands:
```
>s2ctl server --help
Usage: s2ctl server [OPTIONS] COMMAND [ARGS]...

  Manage virtual servers inside your project.

Options:
  --help  Show this message and exit.

Commands:
  add-nic            Add new network interface to a server.
  add-volume         Add new storage volume to a server.
  create             Create new virtual server.
  create-snapshot    Create snapshot of a server.
  delete             Delete a server.
  delete-nic         Remove a network interface from a server.
  delete-snapshot    Remove a snapshot of a server.
  delete-volume      Remove a storage volume from a server.
  edit-volume        Resize a storage volume.
  get                Get information about a server.
  get-nic            Get information about a network interface.
  get-volume         Get information about a storage volume.
  list               Display all virtual servers in the project.
  list-nic           Display all network interfaces of a server.
  list-snapshot      Display all snapshots of a server.
  list-volume        Display all storage volumes of a server.
  power-off          Turn a server off.
  power-on           Turn a server on.
  reboot             Reboot a server.
  rollback-snapshot  Rollback a server to a saved snapshot.
```

Or list of command arguments along with command descirption:
```
>s2ctl server create --help
Usage: s2ctl server create [OPTIONS]

  Create new virtual server.

Options:
  -o, --output [yaml|json|table]  [default: yaml]
  --name TEXT                     Name of new server.  [required]
  --location TEXT                 Where to create a server (see "locations"
                                  command).  [required]

  --image TEXT                    OS images which you want to use for new
                                  server,  [required]

  --cpu TEXT                      CPU cores count.  [required]
  --ram <INT{M|G}>                RAM size (e.g. 1024, 1024M or 1G for 1Gb of
                                  RAM)  [required]

  --volume <(NAME:)SIZE{M|G}>     Volume size in form VolumeName:VolumeSize.
                                  May be multiple. The first specified volume
                                  becomes system (boot) and its name is
                                  ignored. Therefore it can be skipped. E.g. "
                                  --volume 10240 --volume Second:30G" will
                                  create a server with 10Gb system (boot)
                                  volume and 30Gb volume named "Second".
                                  [required]

  --ssh-key INTEGER               Identifier of a SSH key which you want to
                                  use to access a server (see "ssh-key"
                                  command). May be multiple.

  --wait
  --help                          Show this message and exit.
```
