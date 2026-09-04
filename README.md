# Serverspace CLI

`s2ctl` is Serverspace on the command line. It brings ability to control your infrastructure in terminal as you already used to do it via web.

## Installation

`s2ctl` is available for Linux and Windows as single binary. Just download it from [Github](https://github.com/itglobalcom/s2ctl/releases) and extract.

### To install on Linux

The binary is linked against glibc 2.28, so it runs on RHEL / Rocky / AlmaLinux 8
and newer, Debian 10 and newer, Ubuntu 18.10 and newer. On an older distribution
install `s2ctl` from sources (Python 3.11 or newer is required).

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

### Configuration file

Contexts, the keyring holding your API keys and the address of the API live in
`config.yaml`. Its path is printed by `s2ctl --help` as the default of the
`--config` option; another file may be passed explicitly:
`s2ctl -c ./stand.yaml server list`.

| Key | Meaning |
| --- | --- |
| `contexts`, `current_context` | contexts created by `s2ctl context create` and the one currently selected |
| `keyring`, `keyring_key` | the file keyring where the API keys of the contexts are kept, and its password. Both are created next to the configuration file itself, so every configuration file has a keyring of its own |
| `host` | base URL of the API. Optional |

Without `host` the API address is chosen by the two leading characters of the
API key — every installation of the platform has its own prefix. Set `host`
to reach an installation whose prefix `s2ctl` does not know yet, a test stand
for instance:

```yaml
# ~/.config/serverspace.s2ctl/config.yaml
host: https://api.ss4test.com
```

The key is read for every command, so a stand is usually kept in a separate
configuration file passed with `-c`.

## Autocompletion

`s2ctl` uses the completion mechanism built into click: the shell asks `s2ctl`
itself for completions, so nothing but a single line in the shell startup file
is needed. The `install-autocomplete` command adds that line for you:

```
>s2ctl install-autocomplete
shell: bash
installed_in: /home/user/.bashrc
```

The shell (`bash`, `zsh` or `fish`) and the startup file may be passed
explicitly: `s2ctl install-autocomplete zsh ~/.zshrc`. Restart the shell
afterwards. To do the same by hand, add the line for your shell:

```
# ~/.bashrc
eval "$(_S2CTL_COMPLETE=bash_source s2ctl)"

# ~/.zshrc
eval "$(_S2CTL_COMPLETE=zsh_source s2ctl)"

# ~/.config/fish/completions/s2ctl.fish
_S2CTL_COMPLETE=fish_source s2ctl | source
```

Some commands of the previous releases behave differently now:

- `install-autocomplete` writes the line above instead of the completion script it
  used to generate;
- the commands taking an identifier of an isolated network (`network get`,
  `network edit`, `network delete`, `network add-tag`, `network delete-tag` and
  `server add-nic`) reject a malformed identifier themselves — with the expected
  format and the exit code `2` of a usage error, instead of asking the API and
  reporting its refusal;
- an empty collection from the API is printed as a document of the chosen format
  (`[]` with `--output json`, `{}` with `--output yaml`) instead of the empty
  output of the previous releases, so `gateway get-firewall`, `gateway get-nat`,
  `server list` and any other reading command give a script something to parse
  when the project has none of the resources yet. With `--output table` an empty
  collection still prints nothing: that is what an empty table looks like.

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
  -c, --config PATH  [default: /home/user/.config/serverspace.s2ctl/config.yaml]
  -k, --apikey TEXT
  -h, --help         Show this message and exit.

Commands:
  affinity-group        Manage affinity and anti-affinity groups of servers.
  ansible               Set of ansible management commands.
  applications          List of applications which you can install on...
  context               Contexts are used for accessing concrete projects.
  domain                Manage dns domains and records.
  gateway               Manage edge gateways connecting isolated networks...
  images                List of OS images which you can use for your server.
  install-autocomplete  Install autocompletion.
  locations             List of places where our data centers are located.
  network               Manage isolated networks without Internet access.
  project               Various actions related to projects — containers...
  server                Manage virtual servers inside your project.
  ssh-key               SSH keys management.
  task                  Many actions are long-running (e.g.
  vmware                Manage VMware Cloud resources: catalogs, networks...
```

Or get list of second-level commands:
```
>s2ctl server --help
Usage: s2ctl server [OPTIONS] COMMAND [ARGS]...

  Manage virtual servers inside your project.

  Commands take the server id in the l<location>s<server> format, as printed
  by "list".

Options:
  -h, --help  Show this message and exit.

Commands:
  add-nic            Add new network interface to a server.
  add-tag            Add tag to server.
  add-volume         Add new storage volume to a server.
  create             Create new virtual server.
  create-snapshot    Create snapshot of a server.
  delete             Delete a server.
  delete-nic         Remove a network interface from a server.
  delete-snapshot    Remove a snapshot of a server.
  delete-tag         Remove tag from server.
  delete-volume      Remove a storage volume from a server.
  edit               Change only the specified parameters of a server...
  edit-nic           Change bandwidth of a network interface.
  edit-volume        Resize a storage volume.
  get                Get information about a server.
  get-nic            Get information about a network interface.
  get-snapshot       Get information about a snapshot of a server.
  get-volume         Get information about a storage volume.
  list               Display all virtual servers in the project.
  list-nic           Display all network interfaces of a server.
  list-snapshot      Display all snapshots of a server.
  list-volume        Display all storage volumes of a server.
  power-off          Turn a server off.
  power-on           Turn a server on.
  price              Get the monthly price of a server configuration.
  reboot             Reboot a server.
  rename             Change the name of a server.
  rollback-snapshot  Rollback a server to a saved snapshot.
  set-configuration  Set the whole server configuration: both CPU cores...
```

Or list of command arguments along with command descirption:
```
>s2ctl server create --help
Usage: s2ctl server create [OPTIONS]

  Create new virtual server.

Options:
  -o, --output [yaml|json|table]  format of the printed result: yaml and json
                                  are machine-readable, for a script that
                                  parses the output; table is for reading by a
                                  human.  [default: yaml]
  --wait                          wait for task to complete.
  --timeout INTEGER RANGE         seconds to wait for the task, 480 by
                                  default; makes sense only together with
                                  --wait.  [x>=1]
  --name TEXT                     Name of new server.  [required]
  --location TEXT                 Where to create a server (see "locations"
                                  command).  [required]
  --image TEXT                    OS images which you want to use for new
                                  server.  [required]
  --cpu TEXT                      CPU cores count.  [required]
  --ram <INT{M|G}>                RAM size (e.g. 1024, 1024M or 1G for 1Gb of
                                  RAM).  [required]
  --volume <(NAME:)SIZE{M|G}>     Volume size in form VolumeName:VolumeSize.
                                  May be multiple. The first specified volume
                                  becomes system (boot) and its name is
                                  ignored. Therefore it can be skipped. E.g. "
                                  --volume 10240 --volume Second:30G" will
                                  create a server with 10Gb system (boot)
                                  volume and 30Gb volume named "Second".
                                  [required]
  --public-network INTEGER        Bandwidth of the public network interface in
                                  Mbps. May be multiple to create several
                                  interfaces with appropriate bandwidths.
                                  [required]
  --ssh-key INTEGER               Identifier of a SSH key which you want to
                                  use to access a server (see "ssh-key"
                                  command). May be multiple.
  -h, --help                      Show this message and exit.
```

### Command groups

| Group | What it manages |
| --- | --- |
| `context` | contexts — API keys of your projects, kept on this machine |
| `project` | the project the current context points to |
| `locations`, `images`, `applications` | catalogues of the vStack service |
| `server` | vStack servers with their volumes, network interfaces, snapshots and tags |
| `network` | vStack isolated networks |
| `gateway` | vStack edge gateways connecting isolated networks to the Internet |
| `affinity-group` | vStack affinity and anti-affinity groups of servers |
| `vmware` | VMware Cloud: catalogues and the `network`, `edge` and `server` subgroups |
| `domain` | DNS domains and their records |
| `ssh-key` | SSH keys injected into new Linux servers |
| `task` | state of a long-running operation |
| `ansible` | ansible inventory built from the servers of the project |

The `vmware` group is three-level: it follows the structure of the service,
where servers, networks and the edge gateway of a routed network are managed by
their own subgroups.

```
>s2ctl vmware --help
Usage: s2ctl vmware [OPTIONS] COMMAND [ARGS]...

  Manage VMware Cloud resources: catalogs, networks and their edge gateways.

  Ids of VMware resources are plain integers, not the composite ids of the
  vStack sections.

Options:
  -h, --help  Show this message and exit.

Commands:
  edge        Manage the edge gateway of a routed VMware network.
  gpu-models  List of GPU models which you can attach to your VMware server.
  images      List of OS templates which you can use for your VMware server.
  locations   List of VMware locations available to the project.
  network     Manage VMware networks.
  server      Manage VMware servers.
```

### Edge gateways of isolated networks

An edge gateway gives isolated vStack networks a way to the Internet. It is
created for a location and up to three isolated networks at once, and carries a
firewall and a NAT rule set:

```
>s2ctl gateway create --location am2 --name gw --network-id l1n123 --bandwidth 100 --wait
>s2ctl gateway add-nic l1e456 --network-id l1n124 --wait
>s2ctl gateway get-firewall l1e456 --output json > firewall.json
>s2ctl gateway replace-firewall l1e456 --rules-file firewall.json --wait
>s2ctl gateway stop l1e456 --wait
```

The identifier of a gateway has the form `l<location>e<gateway>`, the same shape
the API uses. A malformed identifier is rejected by `s2ctl` itself, before the
request is sent.

### Affinity groups

An affinity group keeps its servers on one host of the location, an
anti-affinity group spreads them over different hosts:

```
>s2ctl affinity-group create --location am2 --name web --anti-affinity
>s2ctl affinity-group list
>s2ctl affinity-group delete l1g789 --wait
```

### VMware Cloud

The VMware service has its own catalogues, networks and servers, addressed by
plain numeric identifiers:

```
>s2ctl vmware locations
>s2ctl vmware images --location 1 --gpu unsupported
>s2ctl vmware network create-routed --location 1 --name app --address 10.0.0.0 --mask 24 --bandwidth 100 --wait
>s2ctl vmware server create --location 1 --name db --image 42 --cpu 4 --ram 8192 \
    --system-disk-size 51200 --system-disk-type "SSD" --public-network 15 --wait
>s2ctl vmware server power-off 1234 --wait
```

Unlike vStack servers, VMware servers have a separate command for every power
transition: `power-on`, `power-off` (cut the power), `shutdown` (ask the guest
OS), `reboot` (ask the guest OS) and `reset`.

`vmware server rebuild` does not reinstall a server in place: the contract orders a
new server from the template and retires the given one, so the command answers with
a **new** identifier. The old one stays readable in state `deleting` while the
platform removes the server and answers `object not found` afterwards — a script
that rebuilds a server has to go on with the identifier the command printed.

The edge gateway of a routed network is managed by the `vmware edge` subgroup —
its firewall, NAT rules and IPsec VPN tunnels:

```
>s2ctl vmware edge get-nat 77 --output json
>s2ctl vmware edge upsert-nat-rule 77 --type DNAT --protocol TCP \
    --original-ip 203.0.113.10 --original-port 443 --translated-ip 10.0.0.5 --translated-port 443 --wait
>s2ctl vmware edge delete-nat-rule 77 --rule-id 3 --wait
```

For a DNAT rule `--original-ip` is the external address of the edge gateway itself,
and no read operation of the contract publishes it: neither the network nor any
other VMware resource carries the field. The address is visible only in the rules of
an edge that already has them (`vmware edge get-nat`) and in the `local_ip` of a VPN
tunnel (`vmware edge get-vpn`), so for an edge without either it has to be learned
outside the contract before the first rule can be written.

`upsert-vpn-tunnel` asks for the IPsec pre-shared key interactively; in a script
pass it in `S2CTL_VPN_SHARED_KEY` instead of `--shared-key`, so that the secret
stays out of `ps`, of the shell history and of the log of a CI job.

`vmware edge set-bandwidth` does not change the bandwidth: the platform accepts
the task and completes it successfully, while the network keeps its previous
value — the operation applies nothing on the platform side. Use
`vmware network set-bandwidth`, which writes the bandwidth of the same network
through `PUT /api/v1/vmware/networks/{network_id}`.

### Rule sets

Firewall and NAT of a vStack gateway are replaced as a whole set, not rule by
rule: read the current set with the matching `get-*` command in JSON, edit the
file and pass it back with `--rules-file` (`-` reads the set from stdin). The
same holds for the firewall of a VMware server and of a VMware edge gateway.
`vmware edge get-firewall` prints the rules inside an object, together with the
state of the firewall itself; `--rules-file` accepts that object as it is and
takes the rules out of it.

The round trip is lossy in one pair of the four: `vmware edge update-firewall`.
The request of the API declares neither `enabled` nor `description` of a rule,
while `get-firewall` prints both, so these two fields of the file are dropped —
CLI has nowhere to send them. In the other three pairs the set comes back as it
was printed.

In a rule of `gateway replace-firewall` and `gateway replace-nat` every field
has to be written out. A field left out is not "keep it as it is": the API reads
a missing `action`, `direction`, `protocol` or `type` as the first value of its
dictionary — `Allow`, `In`, `ICMP` and `SNAT` — and accepts such a rule without
a word. The file goes to the API as it is, `s2ctl` fills nothing in.

A set with no rules in it is printed as a document of the chosen format: `[]`
with `--output json`, `{}` with `--output yaml`, and empty output with
`--output table`, which is what an empty table looks like. So on a gateway that
has no firewall or NAT rules yet `get-firewall` and `get-nat` write a file a
script can parse. `--rules-file` also accepts a file of zero bytes and reads it
as the empty set — the round trip closes on an empty set whichever format the set
was taken in.

### Waiting for a task

Operations that change something are performed by the platform asynchronously:
the command returns the identifier of a task, and the task is done when the
platform has applied the change. Without `--wait` the command prints the
identifier — machine-readable with `--output json` — and returns immediately:

```
>s2ctl server create --name web --location am2 --image ubuntu-22 --cpu 2 --ram 4G --volume 20G --public-network 100 --output json
{"task_id": "l1t9876"}
```

With `--wait` the command waits for the task to complete and prints the affected
resource instead. The state of a task can also be read at any time by its
identifier — of any service, whatever the shape of the identifier:

```
>s2ctl task get l1t9876
```

How long `--wait` waits is limited by `--timeout`, in seconds. Operations differ
in duration by an order of magnitude: powering a server off, writing a DNS record
and creating an isolated network take 6 to 13 seconds, creating a gateway or
switching its power 20 to 25, deleting a VMware server about half a minute,
creating a routed VMware network a minute, copying a server a little over two
minutes, ordering a VMware server around three — the platform installs the
template and customizes the guest OS — and rebuilding one 296 seconds, the
longest operation measured. The default of 480 seconds covers that one with room
for a loaded platform; raise it for what the measurements do not cover, such as a
server with a disk far larger than theirs:

```
>s2ctl vmware server copy 1234 --name web-copy --wait --timeout 900
```

`--timeout` only makes sense together with `--wait`, and the command refuses it
without it. When the time is up, the command reports an error, but the task
itself is not canceled: the platform goes on applying the change, and the task
can be followed by its identifier with `s2ctl task get`.

Four VMware commands print the whole set of resources of the server instead of
the single resource they created: `vmware server add-volume` prints all volumes
of the server, `vmware server connect-client-network`,
`vmware server connect-shared-network` and `vmware server edit-nic` print all
its network interfaces. The contract carries the identifier of the new volume or
interface neither in the response of the operation nor in the task, so there is
nothing to single out.

## Public API coverage

`s2ctl` covers **132 of the 148 operations** of the Public API — every section of
the contract except Kubernetes. The table below maps every covered operation to
the command that performs it; the 16 operations left out are listed after it.

> How the operations are counted: the denominator is the set of routes declared
> by the controllers of the Public API, with the paths given by route constants
> expanded. A count that reads literal paths only misses three of them — the read
> and the deletion of an affinity group and `GET /api/v1/tasks/already_completed_task`
> — and gives 143 instead of 146; two more VMware operations
> (`nested-hypervisor/enable` and `nested-hypervisor/disable`) have been published
> since, which brings the surface to 148.

The mapping is not one-to-one:

- `task get` reads a task of any service, so a single command covers all four
  shapes of a task identifier;
- `server power-off` and `server reboot` cover two operations each, chosen by
  `--hard`: `power/shutdown` and `power/off`, `power/reboot` and `power/reset`.
  These two vStack commands are older than the rule of one command per operation
  and keep their arguments for compatibility; in the VMware section every power
  transition has its own command;
- `PUT /api/v1/vmware/networks/{network_id}` changes both the name and the
  bandwidth of a network, so it is split into `vmware network rename` and
  `vmware network set-bandwidth`;
- seven commands map to no operation of the contract at all: the five `context`
  commands (contexts and their API keys live on this machine),
  `install-autocomplete` and `ansible get-inventory`, which builds an inventory
  from the list of servers it has already read.

The table is kept honest by `tests/s2ctl/test_command_coverage.py`: an operation
left without a command, a command missing from the table and a command for an
operation out of scope all fail the tests.

### Covered operations

#### Project, catalogues and SSH keys — 8

| Operation | Command |
| --- | --- |
| `GET /api/v1/applications` | `s2ctl applications` |
| `GET /api/v1/images` | `s2ctl images` |
| `GET /api/v1/locations` | `s2ctl locations` |
| `GET /api/v1/project` | `s2ctl project show` |
| `GET /api/v1/ssh-keys` | `s2ctl ssh-key list` |
| `POST /api/v1/ssh-keys` | `s2ctl ssh-key create` |
| `GET /api/v1/ssh-keys/{ssh_key_id}` | `s2ctl ssh-key get` |
| `DELETE /api/v1/ssh-keys/{ssh_key_id}` | `s2ctl ssh-key delete` |

#### Tasks — 4

| Operation | Command |
| --- | --- |
| `GET /api/v1/tasks/already_completed_task` | `s2ctl task get` |
| `GET /api/v1/tasks/dns{task_id}` | `s2ctl task get` |
| `GET /api/v1/tasks/vmw{task_id}` | `s2ctl task get` |
| `GET /api/v1/tasks/{task_id}` | `s2ctl task get` |

#### vStack servers — 30

| Operation | Command |
| --- | --- |
| `GET /api/v1/servers` | `s2ctl server list` |
| `POST /api/v1/servers` | `s2ctl server create` |
| `POST /api/v1/servers/price` | `s2ctl server price` |
| `GET /api/v1/servers/{server_id}` | `s2ctl server get` |
| `PUT /api/v1/servers/{server_id}` | `s2ctl server set-configuration` |
| `PATCH /api/v1/servers/{server_id}` | `s2ctl server edit` |
| `DELETE /api/v1/servers/{server_id}` | `s2ctl server delete` |
| `PUT /api/v1/servers/{server_id}/name` | `s2ctl server rename` |
| `GET /api/v1/servers/{server_id}/nics` | `s2ctl server list-nic` |
| `POST /api/v1/servers/{server_id}/nics` | `s2ctl server add-nic` |
| `GET /api/v1/servers/{server_id}/snapshots` | `s2ctl server list-snapshot` |
| `POST /api/v1/servers/{server_id}/snapshots` | `s2ctl server create-snapshot` |
| `POST /api/v1/servers/{server_id}/tags` | `s2ctl server add-tag` |
| `GET /api/v1/servers/{server_id}/volumes` | `s2ctl server list-volume` |
| `POST /api/v1/servers/{server_id}/volumes` | `s2ctl server add-volume` |
| `GET /api/v1/servers/{server_id}/nics/{nic_id}` | `s2ctl server get-nic` |
| `PUT /api/v1/servers/{server_id}/nics/{nic_id}` | `s2ctl server edit-nic` |
| `DELETE /api/v1/servers/{server_id}/nics/{nic_id}` | `s2ctl server delete-nic` |
| `POST /api/v1/servers/{server_id}/power/off` | `s2ctl server power-off` |
| `POST /api/v1/servers/{server_id}/power/on` | `s2ctl server power-on` |
| `POST /api/v1/servers/{server_id}/power/reboot` | `s2ctl server reboot` |
| `POST /api/v1/servers/{server_id}/power/reset` | `s2ctl server reboot` |
| `POST /api/v1/servers/{server_id}/power/shutdown` | `s2ctl server power-off` |
| `GET /api/v1/servers/{server_id}/snapshots/{snapshot_id}` | `s2ctl server get-snapshot` |
| `DELETE /api/v1/servers/{server_id}/snapshots/{snapshot_id}` | `s2ctl server delete-snapshot` |
| `DELETE /api/v1/servers/{server_id}/tags/{tag}` | `s2ctl server delete-tag` |
| `GET /api/v1/servers/{server_id}/volumes/{volume_id}` | `s2ctl server get-volume` |
| `PUT /api/v1/servers/{server_id}/volumes/{volume_id}` | `s2ctl server edit-volume` |
| `DELETE /api/v1/servers/{server_id}/volumes/{volume_id}` | `s2ctl server delete-volume` |
| `POST /api/v1/servers/{server_id}/snapshots/{snapshot_id}/rollback` | `s2ctl server rollback-snapshot` |

#### vStack isolated networks — 7

| Operation | Command |
| --- | --- |
| `GET /api/v1/networks/isolated` | `s2ctl network list` |
| `POST /api/v1/networks/isolated` | `s2ctl network create` |
| `GET /api/v1/networks/isolated/{network_id}` | `s2ctl network get` |
| `PUT /api/v1/networks/isolated/{network_id}` | `s2ctl network edit` |
| `DELETE /api/v1/networks/isolated/{network_id}` | `s2ctl network delete` |
| `POST /api/v1/networks/isolated/{network_id}/tags` | `s2ctl network add-tag` |
| `DELETE /api/v1/networks/isolated/{network_id}/tags/{tag}` | `s2ctl network delete-tag` |

#### vStack affinity groups — 4

| Operation | Command |
| --- | --- |
| `GET /api/v1/affinity-groups` | `s2ctl affinity-group list` |
| `POST /api/v1/affinity-groups` | `s2ctl affinity-group create` |
| `GET /api/v1/affinity-groups/{affinity_group_id}` | `s2ctl affinity-group get` |
| `DELETE /api/v1/affinity-groups/{affinity_group_id}` | `s2ctl affinity-group delete` |

#### vStack edge gateways — 17

| Operation | Command |
| --- | --- |
| `GET /api/v1/gateways` | `s2ctl gateway list` |
| `POST /api/v1/gateways` | `s2ctl gateway create` |
| `GET /api/v1/gateways/l{location_id}e{gateway_id}` | `s2ctl gateway get` |
| `PUT /api/v1/gateways/l{location_id}e{gateway_id}` | `s2ctl gateway rename` |
| `DELETE /api/v1/gateways/l{location_id}e{gateway_id}` | `s2ctl gateway delete` |
| `PUT /api/v1/gateways/l{location_id}e{gateway_id}/bandwidth` | `s2ctl gateway set-bandwidth` |
| `GET /api/v1/gateways/l{location_id}e{gateway_id}/firewall` | `s2ctl gateway get-firewall` |
| `PUT /api/v1/gateways/l{location_id}e{gateway_id}/firewall` | `s2ctl gateway replace-firewall` |
| `GET /api/v1/gateways/l{location_id}e{gateway_id}/nat` | `s2ctl gateway get-nat` |
| `PUT /api/v1/gateways/l{location_id}e{gateway_id}/nat` | `s2ctl gateway replace-nat` |
| `POST /api/v1/gateways/l{location_id}e{gateway_id}/nics` | `s2ctl gateway add-nic` |
| `POST /api/v1/gateways/l{location_id}e{gateway_id}/restart` | `s2ctl gateway restart` |
| `POST /api/v1/gateways/l{location_id}e{gateway_id}/start` | `s2ctl gateway start` |
| `POST /api/v1/gateways/l{location_id}e{gateway_id}/stop` | `s2ctl gateway stop` |
| `POST /api/v1/gateways/l{location_id}e{gateway_id}/tags` | `s2ctl gateway add-tag` |
| `DELETE /api/v1/gateways/l{location_id}e{gateway_id}/nics/{nic_id}` | `s2ctl gateway delete-nic` |
| `DELETE /api/v1/gateways/l{location_id}e{gateway_id}/tags/{tag}` | `s2ctl gateway delete-tag` |

#### DNS domains and records — 9

| Operation | Command |
| --- | --- |
| `GET /api/v1/domains` | `s2ctl domain list` |
| `POST /api/v1/domains` | `s2ctl domain create` |
| `GET /api/v1/domains/{domain_name}` | `s2ctl domain get` |
| `DELETE /api/v1/domains/{domain_name}` | `s2ctl domain delete` |
| `GET /api/v1/domains/{domain_name}/records` | `s2ctl domain list-record` |
| `POST /api/v1/domains/{domain_name}/records` | `s2ctl domain create-record` |
| `GET /api/v1/domains/{domain_name}/records/{record_id}` | `s2ctl domain get-record` |
| `PUT /api/v1/domains/{domain_name}/records/{record_id}` | `s2ctl domain update-record` |
| `DELETE /api/v1/domains/{domain_name}/records/{record_id}` | `s2ctl domain delete-record` |

#### VMware catalogues — 3

| Operation | Command |
| --- | --- |
| `GET /api/v1/vmware/gpu-models` | `s2ctl vmware gpu-models` |
| `GET /api/v1/vmware/images` | `s2ctl vmware images` |
| `GET /api/v1/vmware/locations` | `s2ctl vmware locations` |

#### VMware networks and their edge gateways — 17

| Operation | Command |
| --- | --- |
| `GET /api/v1/vmware/networks` | `s2ctl vmware network list` |
| `POST /api/v1/vmware/networks/isolated` | `s2ctl vmware network create-isolated` |
| `POST /api/v1/vmware/networks/public` | `s2ctl vmware network create-public` |
| `POST /api/v1/vmware/networks/routed` | `s2ctl vmware network create-routed` |
| `GET /api/v1/vmware/networks/{network_id}` | `s2ctl vmware network get` |
| `PUT /api/v1/vmware/networks/{network_id}` | `s2ctl vmware network rename`<br>`s2ctl vmware network set-bandwidth` |
| `DELETE /api/v1/vmware/networks/{network_id}` | `s2ctl vmware network delete` |
| `POST /api/v1/vmware/networks/{network_id}/servers` | `s2ctl vmware network connect-servers` |
| `PUT /api/v1/vmware/networks/{network_id}/edge/bandwidth` | `s2ctl vmware edge set-bandwidth` |
| `GET /api/v1/vmware/networks/{network_id}/edge/firewall` | `s2ctl vmware edge get-firewall` |
| `PUT /api/v1/vmware/networks/{network_id}/edge/firewall` | `s2ctl vmware edge update-firewall` |
| `GET /api/v1/vmware/networks/{network_id}/edge/nat` | `s2ctl vmware edge get-nat` |
| `POST /api/v1/vmware/networks/{network_id}/edge/nat` | `s2ctl vmware edge upsert-nat-rule` |
| `GET /api/v1/vmware/networks/{network_id}/edge/vpn` | `s2ctl vmware edge get-vpn` |
| `POST /api/v1/vmware/networks/{network_id}/edge/vpn` | `s2ctl vmware edge upsert-vpn-tunnel` |
| `DELETE /api/v1/vmware/networks/{network_id}/edge/nat/{rule_id}` | `s2ctl vmware edge delete-nat-rule` |
| `DELETE /api/v1/vmware/networks/{network_id}/edge/vpn/{tunnel_id}` | `s2ctl vmware edge delete-vpn-tunnel` |

#### VMware servers — 33

| Operation | Command |
| --- | --- |
| `GET /api/v1/vmware/servers` | `s2ctl vmware server list` |
| `POST /api/v1/vmware/servers` | `s2ctl vmware server create` |
| `POST /api/v1/vmware/servers/verify` | `s2ctl vmware server verify` |
| `GET /api/v1/vmware/servers/{server_id}` | `s2ctl vmware server get` |
| `PUT /api/v1/vmware/servers/{server_id}` | `s2ctl vmware server set-configuration` |
| `DELETE /api/v1/vmware/servers/{server_id}` | `s2ctl vmware server delete` |
| `PUT /api/v1/vmware/servers/{server_id}/computer-name` | `s2ctl vmware server set-computer-name` |
| `POST /api/v1/vmware/servers/{server_id}/copy` | `s2ctl vmware server copy` |
| `GET /api/v1/vmware/servers/{server_id}/firewall` | `s2ctl vmware server get-firewall` |
| `PUT /api/v1/vmware/servers/{server_id}/firewall` | `s2ctl vmware server replace-firewall` |
| `PUT /api/v1/vmware/servers/{server_id}/name` | `s2ctl vmware server rename` |
| `GET /api/v1/vmware/servers/{server_id}/nics` | `s2ctl vmware server list-nic` |
| `POST /api/v1/vmware/servers/{server_id}/nics` | `s2ctl vmware server connect-client-network` |
| `POST /api/v1/vmware/servers/{server_id}/rebuild` | `s2ctl vmware server rebuild` |
| `GET /api/v1/vmware/servers/{server_id}/snapshot` | `s2ctl vmware server get-snapshot` |
| `POST /api/v1/vmware/servers/{server_id}/snapshot` | `s2ctl vmware server create-snapshot` |
| `DELETE /api/v1/vmware/servers/{server_id}/snapshot` | `s2ctl vmware server delete-snapshot` |
| `GET /api/v1/vmware/servers/{server_id}/volumes` | `s2ctl vmware server list-volume` |
| `POST /api/v1/vmware/servers/{server_id}/volumes` | `s2ctl vmware server add-volume` |
| `POST /api/v1/vmware/servers/{server_id}/nested-hypervisor/disable` | `s2ctl vmware server disable-nested-hypervisor` |
| `POST /api/v1/vmware/servers/{server_id}/nested-hypervisor/enable` | `s2ctl vmware server enable-nested-hypervisor` |
| `POST /api/v1/vmware/servers/{server_id}/nics/shared` | `s2ctl vmware server connect-shared-network` |
| `PUT /api/v1/vmware/servers/{server_id}/nics/{nic_id}` | `s2ctl vmware server edit-nic` |
| `DELETE /api/v1/vmware/servers/{server_id}/nics/{nic_id}` | `s2ctl vmware server disconnect-nic` |
| `POST /api/v1/vmware/servers/{server_id}/power/off` | `s2ctl vmware server power-off` |
| `POST /api/v1/vmware/servers/{server_id}/power/on` | `s2ctl vmware server power-on` |
| `POST /api/v1/vmware/servers/{server_id}/power/reboot` | `s2ctl vmware server reboot` |
| `POST /api/v1/vmware/servers/{server_id}/power/reset` | `s2ctl vmware server reset` |
| `POST /api/v1/vmware/servers/{server_id}/power/shutdown` | `s2ctl vmware server shutdown` |
| `POST /api/v1/vmware/servers/{server_id}/snapshot/restore` | `s2ctl vmware server restore-snapshot` |
| `GET /api/v1/vmware/servers/{server_id}/volumes/{volume_id}` | `s2ctl vmware server get-volume` |
| `PUT /api/v1/vmware/servers/{server_id}/volumes/{volume_id}` | `s2ctl vmware server edit-volume` |
| `DELETE /api/v1/vmware/servers/{server_id}/volumes/{volume_id}` | `s2ctl vmware server delete-volume` |

### Not covered: Kubernetes

Kubernetes clusters are not managed by `s2ctl`. The section is absent from the
published API reference and its service is under maintenance only, so there is no
partial support either — none of the 16 operations below has a command.

| Operation |
| --- |
| `GET /api/v1/k8s_clusters` |
| `POST /api/v1/k8s_clusters` |
| `GET /api/v1/k8s_versions` |
| `GET /api/v1/k8s_clusters/{cluster_id}` |
| `PUT /api/v1/k8s_clusters/{cluster_id}` |
| `DELETE /api/v1/k8s_clusters/{cluster_id}` |
| `GET /api/v1/tasks/k8s_{task_id}` |
| `GET /api/v1/k8s_clusters/{cluster_id}/k8s_versions` |
| `GET /api/v1/k8s_clusters/{cluster_id}/node_groups` |
| `POST /api/v1/k8s_clusters/{cluster_id}/node_groups` |
| `POST /api/v1/k8s_clusters/{cluster_id}/tags` |
| `GET /api/v1/k8s_clusters/{cluster_id}/node_groups/{group_id}` |
| `PUT /api/v1/k8s_clusters/{cluster_id}/node_groups/{group_id}` |
| `DELETE /api/v1/k8s_clusters/{cluster_id}/node_groups/{group_id}` |
| `DELETE /api/v1/k8s_clusters/{cluster_id}/tags/{tag}` |
| `POST /api/v1/k8s_clusters/{cluster_id}/node_groups/{group_id}/ingress` |

## Verification status

The commands were run against the production API `api.serverspace.io` on a real
project. What that run covered and what it did not is listed below, so that the
next change knows what is already known to work and what is still only covered
by tests.

Exercised against the live platform:

- the catalogues and every read command of every section;
- vStack edge gateways — all 17 operations: creation, reading, renaming and
  deletion, bandwidth, the firewall and the NAT set both read and written back,
  `add-nic` and `delete-nic`, the three power commands, tags;
- VMware edge gateways — all 9 operations: the firewall, a SNAT rule and a VPN
  tunnel, each created and deleted again;
- VMware servers — ordering a server, `verify`, the power commands, `copy`,
  `rebuild`, `set-computer-name` and deletion;
- volumes, network interfaces and the snapshot of a VMware server — all 14
  operations;
- affinity groups — the whole set of four operations, deletion included, whose
  task the API answers with the synthetic identifier `already_completed_task`;
- DNS — a zone and its records, with the task of the `dns{n}` shape awaited;
- a refusal of the API (401, 403 and 404) turned into a readable message with a
  non-zero exit code and no traceback;
- `--wait` and `--timeout` on real tasks of the platform.

Not exercised against the live platform:

- `vmware server enable-nested-hypervisor` and `disable-nested-hypervisor`: both
  operations answer 404 on production, the feature is not deployed there yet;
- `server price` of the vStack section: the project is answered 403, the service
  is not available to it;
- the Windows binary: it was not built, only the Linux one;
- operations whose resources the project did not have at the time of the run.
