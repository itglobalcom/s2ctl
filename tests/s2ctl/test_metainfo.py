import json

import pytest
import yaml
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from ssclient.metainfo import ImageEntity, LocationEntity
from tests.s2ctl.conftest import APIKEY

# Формы ответов publisher'а целиком: `VstackLocation` и `VstackImage` контракта.
# Команда обязана донести их до вывода без потерь — по этим полям и выбирается
# конфигурация заказа, а другого способа их узнать у CLI нет.
_LOCATION = LocationEntity(
    id='ds1',
    system_volume_min=25600,
    additional_volume_min=1024,
    volume_max=2048000,
    windows_system_volume_min=51200,
    bandwidth_min=10,
    bandwidth_max=1000,
    cpu_quantity_options=[1, 2, 4],
    ram_size_options=[512, 1024, 2048],
)

_IMAGE = ImageEntity(
    id='ds1i123',
    location_id='ds1',
    type='Ubuntu',
    os_version='22.04',
    architecture='X64',
    allow_ssh_keys=True,
)

_CATALOG_CASES = (
    ('locations', 'api/v1/locations', 'locations', _LOCATION),
    ('images', 'api/v1/images', 'images', _IMAGE),
)


@pytest.mark.parametrize('command,path,envelope,entity', _CATALOG_CASES)
def test_catalog_prints_the_entity_of_the_contract_whole(
    cli_http_client, command, path, envelope, entity,
):
    cli_http_client.on('GET', path, {envelope: [entity]})

    result = CliRunner().invoke(entry_point, ('-k', APIKEY, command, '--output=json'))

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('GET') == [path]
    assert json.loads(result.output) == [entity]


# Машинный формат отдаёт значение типом контракта: число числом, булево булевым.
# Иначе `yaml.safe_load` вернёт строку там, где контракт даёт число, и разбор
# yaml-вывода разойдётся с разбором того же ответа в json.
@pytest.mark.parametrize('command,path,envelope,entity', _CATALOG_CASES)
def test_catalog_keeps_the_value_types_of_the_contract_in_yaml(
    cli_http_client, command, path, envelope, entity,
):
    cli_http_client.on('GET', path, {envelope: [entity]})

    result = CliRunner().invoke(entry_point, ('-k', APIKEY, command, '--output=yaml'))

    assert result.exit_code == 0, result.output
    assert yaml.safe_load(result.output) == {entity['id']: entity}


# Каталог приложений фильтруется тремя параметрами запроса, и у каждого своя опция:
# имена опций и имена параметров контракта расходятся (`--application` кладётся
# в `application_id`).
_APPLICATION_FILTERS = (
    (('--location', 'am2'), 'location_id=am2'),
    (('--application', 'docker'), 'application_id=docker'),
    (('--image', 'ubuntu-22-04'), 'image_id=ubuntu-22-04'),
)


@pytest.mark.parametrize('command_args,expected_query', _APPLICATION_FILTERS)
def test_applications_passes_its_filters_to_the_query_of_the_contract(
    cli_http_client, command_args, expected_query,
):
    expected_path = 'api/v1/applications?{query}'.format(query=expected_query)
    cli_http_client.on('GET', expected_path, {'applications': []})

    result = CliRunner().invoke(entry_point, ('-k', APIKEY, 'applications') + command_args)

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('GET') == [expected_path]
