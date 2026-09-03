import pytest

from ssclient.vmware.metainfo import (
    VmwareGpuModelsService,
    VmwareImagesService,
    VmwareLocationsService,
)

LOCATIONS_PATH = 'api/v1/vmware/locations'
IMAGES_PATH = 'api/v1/vmware/images'
GPU_MODELS_PATH = 'api/v1/vmware/gpu-models'

LOCATION_ENTITY = {
    'id': 1,
    'tech_title': 'ru-msk',
    'gpu_supported': True,
    'nested_hypervisor_supported': False,
    'disk_types': [],
}

IMAGE_ENTITY = {
    'id': 7,
    'name': 'Ubuntu 24.04',
    'os_family': 'linux',
    'os_type': 'ubuntu',
    'min_ram_mb': 1024,
    'hdd_gb': 10,
    'ssh_key_supported': True,
    'cpu_hot_add': True,
    'memory_hot_add': True,
    'nic_hot_remove': True,
    'is_gpu_only': False,
    'supported_gpu_model_ids': [],
}

GPU_MODEL_ENTITY = {
    'id': 3,
    'tech_title': 'a100',
    'name': 'NVIDIA A100',
    'capacity_vram_mb': 40960,
    'gpu_card_count': 1,
    'server_allocation_limit': 4,
    'max_server_ram_mb': 262144,
    'is_available': True,
}


async def test_locations_list_unwraps_locations(fake_http_client):
    fake_http_client.on('GET', LOCATIONS_PATH, {'locations': [LOCATION_ENTITY]})

    locations = await VmwareLocationsService(fake_http_client).list()

    assert fake_http_client.paths('GET') == [LOCATIONS_PATH]
    assert locations == [LOCATION_ENTITY]


@pytest.mark.parametrize('location_id,gpu,expected_path', (
    # Пустое значение объявленного параметра publisher не принимает, поэтому
    # незаданный фильтр не уходит в query вовсе.
    (None, None, IMAGES_PATH),
    (1, None, '{path}?location_id=1'.format(path=IMAGES_PATH)),
    (None, 'required', '{path}?gpu=required'.format(path=IMAGES_PATH)),
))
async def test_images_list_sends_only_given_filters(
    fake_http_client, location_id, gpu, expected_path,
):
    fake_http_client.on('GET', expected_path, {'images': [IMAGE_ENTITY]})

    images = await VmwareImagesService(fake_http_client).list(location_id=location_id, gpu=gpu)

    assert fake_http_client.paths('GET') == [expected_path]
    assert images == [IMAGE_ENTITY]


@pytest.mark.parametrize('location_id,expected_path', (
    (None, GPU_MODELS_PATH),
    (1, '{path}?location_id=1'.format(path=GPU_MODELS_PATH)),
))
async def test_gpu_models_list_sends_only_given_filters(
    fake_http_client, location_id, expected_path,
):
    fake_http_client.on('GET', expected_path, {'gpu_models': [GPU_MODEL_ENTITY]})

    gpu_models = await VmwareGpuModelsService(fake_http_client).list(location_id=location_id)

    assert fake_http_client.paths('GET') == [expected_path]
    assert gpu_models == [GPU_MODEL_ENTITY]
